"""Seed reference + demo commercial data so the enquiry-to-delivery flow is runnable end to end.

Lanes covered: China -> UAE, China -> USA, India -> UAE (ocean FCL), matching the PRD2 example
scenarios (ceramic tiles Foshan->Jebel Ali, automotive parts Shanghai->Dubai).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.db import SessionLocal, Base, engine
from app import models
from app.models.reference import Country, Location, Carrier, Service, HSCode, TradeRule, RateCard
from app.models.customer import Customer, CustomerContact


def get_or_create(db, model, defaults=None, **kwargs):
    obj = db.query(model).filter_by(**kwargs).first()
    if obj:
        return obj, False
    params = dict(kwargs)
    params.update(defaults or {})
    obj = model(**params)
    db.add(obj)
    db.flush()
    return obj, True


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # --- Countries ---
    countries = {}
    for iso2, name, region in [
        ("CN", "China", "APAC"),
        ("AE", "United Arab Emirates", "MEA"),
        ("US", "United States", "AMER"),
        ("IN", "India", "APAC"),
        ("GB", "United Kingdom", "EMEA"),
    ]:
        c, _ = get_or_create(db, Country, iso2=iso2, defaults={"name": name, "region": region})
        countries[iso2] = c
    db.flush()

    # --- Locations (city / port) ---
    def loc(name, country_iso, ltype, unlocode=None):
        obj, _ = get_or_create(
            db, Location, name=name, country_id=countries[country_iso].id, location_type=ltype,
            defaults={"unlocode": unlocode},
        )
        return obj

    foshan = loc("Foshan", "CN", "city")
    shanghai = loc("Shanghai", "CN", "city")
    shenzhen_port = loc("Shenzhen (Yantian)", "CN", "port", "CNYTN")
    shanghai_port = loc("Shanghai Port", "CN", "port", "CNSHA")
    jebel_ali = loc("Jebel Ali", "AE", "port", "AEJEA")
    dubai = loc("Dubai", "AE", "city")
    los_angeles_port = loc("Los Angeles", "US", "port", "USLAX")
    los_angeles = loc("Los Angeles", "US", "city")
    nhava_sheva = loc("Nhava Sheva (JNPT)", "IN", "port", "INNSA")
    mumbai = loc("Mumbai", "IN", "city")
    shanghai_airport = loc("Shanghai Pudong Airport", "CN", "airport", "CNPVG")
    dubai_airport = loc("Dubai International Airport", "AE", "airport", "AEDXB")
    db.flush()

    # --- Carriers ---
    msc, _ = get_or_create(db, Carrier, name="MSC", defaults={"scac": "MSCU", "mode": "ocean", "reliability_score": 0.93})
    maersk, _ = get_or_create(db, Carrier, name="Maersk", defaults={"scac": "MAEU", "mode": "ocean", "reliability_score": 0.95})
    cma, _ = get_or_create(db, Carrier, name="CMA CGM", defaults={"scac": "CMDU", "mode": "ocean", "reliability_score": 0.90})
    emirates_cargo, _ = get_or_create(db, Carrier, name="Emirates SkyCargo", defaults={"scac": "EK", "mode": "air", "reliability_score": 0.94})
    cathay_cargo, _ = get_or_create(db, Carrier, name="Cathay Cargo", defaults={"scac": "CX", "mode": "air", "reliability_score": 0.91})
    db.flush()

    # --- Services (lanes) ---
    get_or_create(db, Service, carrier_id=msc.id, origin_location_id=shenzhen_port.id,
                  destination_location_id=jebel_ali.id, defaults={"mode": "ocean", "transit_days": 27, "frequency_per_week": 1})
    get_or_create(db, Service, carrier_id=maersk.id, origin_location_id=shenzhen_port.id,
                  destination_location_id=jebel_ali.id, defaults={"mode": "ocean", "transit_days": 24, "frequency_per_week": 2})
    get_or_create(db, Service, carrier_id=cma.id, origin_location_id=shanghai_port.id,
                  destination_location_id=jebel_ali.id, defaults={"mode": "ocean", "transit_days": 26, "frequency_per_week": 1})
    get_or_create(db, Service, carrier_id=maersk.id, origin_location_id=shanghai_port.id,
                  destination_location_id=los_angeles_port.id, defaults={"mode": "ocean", "transit_days": 16, "frequency_per_week": 2})
    get_or_create(db, Service, carrier_id=msc.id, origin_location_id=nhava_sheva.id,
                  destination_location_id=jebel_ali.id, defaults={"mode": "ocean", "transit_days": 9, "frequency_per_week": 1})
    get_or_create(db, Service, carrier_id=emirates_cargo.id, origin_location_id=shanghai_airport.id,
                  destination_location_id=dubai_airport.id, defaults={"mode": "air", "transit_days": 3, "frequency_per_week": 7})
    get_or_create(db, Service, carrier_id=cathay_cargo.id, origin_location_id=shanghai_airport.id,
                  destination_location_id=dubai_airport.id, defaults={"mode": "air", "transit_days": 4, "frequency_per_week": 5})
    db.flush()

    # --- HS codes (subset relevant to demo commodities) ---
    hs_defs = [
        ("69", "chapter", "Ceramic products", None, False),
        ("6907", "heading", "Ceramic flags and paving, hearth or wall tiles", "69", False),
        ("690721", "subheading", "Ceramic tiles, unglazed, water absorption <=0.5%", "6907", False),
        ("87", "chapter", "Vehicles other than railway, and parts thereof", None, False),
        ("8708", "heading", "Parts and accessories for motor vehicles", "87", False),
        ("870829", "subheading", "Other parts and accessories of bodies (motor vehicles)", "8708", False),
        ("73", "chapter", "Articles of iron or steel", None, False),
        ("7324", "heading", "Sanitary ware and parts thereof, of iron or steel", "73", False),
        ("732410", "subheading", "Sinks and wash basins, of stainless steel", "7324", False),
    ]
    for code, level, desc, parent, dg in hs_defs:
        get_or_create(db, HSCode, code=code, defaults={
            "level": level, "description": desc, "parent_code": parent, "dangerous_goods_flag": dg,
        })
    db.flush()

    # --- Trade rules (document requirements) ---
    trade_rules = [
        dict(country_id=countries["AE"].id, direction="import", hs_scope="69", mode=None,
             requirement_type="document", requirement="Certificate of Origin", severity="required",
             authority="UAE Customs", source="Federal Customs Authority guidance"),
        dict(country_id=countries["AE"].id, direction="import", hs_scope=None, mode=None,
             requirement_type="document", requirement="Commercial Invoice", severity="required",
             authority="UAE Customs", source="Federal Customs Authority guidance"),
        dict(country_id=countries["AE"].id, direction="import", hs_scope=None, mode=None,
             requirement_type="document", requirement="Packing List", severity="required",
             authority="UAE Customs", source="Federal Customs Authority guidance"),
        dict(country_id=countries["AE"].id, direction="import", hs_scope="87", mode=None,
             requirement_type="document", requirement="Import Declaration", severity="required",
             authority="UAE Customs", source="Federal Customs Authority guidance"),
        dict(country_id=countries["AE"].id, direction="import", hs_scope="73", mode=None,
             requirement_type="license", requirement="Conformity certificate for steel goods (ESMA)",
             severity="conditional", authority="ESMA", source="UAE conformity assessment scheme"),
        dict(country_id=countries["US"].id, direction="import", hs_scope=None, mode=None,
             requirement_type="document", requirement="Commercial Invoice", severity="required",
             authority="US CBP", source="CBP entry requirements"),
        dict(country_id=countries["US"].id, direction="import", hs_scope=None, mode=None,
             requirement_type="document", requirement="ISF (10+2) Filing", severity="required",
             authority="US CBP", source="CBP Importer Security Filing"),
    ]
    for tr in trade_rules:
        get_or_create(db, TradeRule, country_id=tr["country_id"], direction=tr["direction"],
                      hs_scope=tr["hs_scope"], requirement=tr["requirement"],
                      defaults={k: v for k, v in tr.items() if k not in ("country_id", "direction", "hs_scope", "requirement")})
    db.flush()

    # --- Rate cards ---
    rate_cards = [
        dict(carrier_id=msc.id, origin_location_id=shenzhen_port.id, destination_location_id=jebel_ali.id,
             equipment="40HC", base_freight=1800, documentation_fee=50, origin_handling_fee=175,
             destination_handling_fee=160, fuel_surcharge_pct=12, free_time_days=7,
             demurrage_tier_json=[{"from_day": 1, "to_day": 3, "rate": 100}, {"from_day": 4, "to_day": 7, "rate": 150}, {"from_day": 8, "to_day": 999, "rate": 250}]),
        dict(carrier_id=maersk.id, origin_location_id=shenzhen_port.id, destination_location_id=jebel_ali.id,
             equipment="40HC", base_freight=2100, documentation_fee=55, origin_handling_fee=180,
             destination_handling_fee=165, fuel_surcharge_pct=11, free_time_days=7,
             demurrage_tier_json=[{"from_day": 1, "to_day": 4, "rate": 120}, {"from_day": 5, "to_day": 999, "rate": 200}]),
        dict(carrier_id=cma.id, origin_location_id=shanghai_port.id, destination_location_id=jebel_ali.id,
             equipment="40HC", base_freight=1950, documentation_fee=50, origin_handling_fee=170,
             destination_handling_fee=160, fuel_surcharge_pct=13, free_time_days=5,
             demurrage_tier_json=[{"from_day": 1, "to_day": 5, "rate": 110}, {"from_day": 6, "to_day": 999, "rate": 220}]),
        dict(carrier_id=maersk.id, origin_location_id=shanghai_port.id, destination_location_id=los_angeles_port.id,
             equipment="40HC", base_freight=2600, documentation_fee=60, origin_handling_fee=200,
             destination_handling_fee=210, fuel_surcharge_pct=14, free_time_days=4,
             demurrage_tier_json=[{"from_day": 1, "to_day": 4, "rate": 150}, {"from_day": 5, "to_day": 999, "rate": 275}]),
        dict(carrier_id=msc.id, origin_location_id=nhava_sheva.id, destination_location_id=jebel_ali.id,
             equipment="40HC", base_freight=650, documentation_fee=35, origin_handling_fee=90,
             destination_handling_fee=110, fuel_surcharge_pct=9, free_time_days=7,
             demurrage_tier_json=[{"from_day": 1, "to_day": 7, "rate": 60}, {"from_day": 8, "to_day": 999, "rate": 120}]),
        dict(carrier_id=emirates_cargo.id, origin_location_id=shanghai_airport.id, destination_location_id=dubai_airport.id,
             equipment="AIR_PALLET", base_freight=420, documentation_fee=40, origin_handling_fee=60,
             destination_handling_fee=70, fuel_surcharge_pct=18, free_time_days=2,
             demurrage_tier_json=[{"from_day": 1, "to_day": 2, "rate": 50}, {"from_day": 3, "to_day": 999, "rate": 90}]),
        dict(carrier_id=cathay_cargo.id, origin_location_id=shanghai_airport.id, destination_location_id=dubai_airport.id,
             equipment="AIR_PALLET", base_freight=360, documentation_fee=40, origin_handling_fee=55,
             destination_handling_fee=65, fuel_surcharge_pct=16, free_time_days=2,
             demurrage_tier_json=[{"from_day": 1, "to_day": 2, "rate": 45}, {"from_day": 3, "to_day": 999, "rate": 85}]),
    ]
    for rc in rate_cards:
        get_or_create(db, RateCard, carrier_id=rc["carrier_id"], origin_location_id=rc["origin_location_id"],
                      destination_location_id=rc["destination_location_id"], equipment=rc["equipment"],
                      defaults={k: v for k, v in rc.items() if k not in ("carrier_id", "origin_location_id", "destination_location_id", "equipment")})
    db.flush()

    # --- Demo customers ---
    global_trading, _ = get_or_create(db, Customer, name="Al Fahim Global Trading LLC",
                                       defaults={"account_owner": "Saurabh", "default_incoterm": "DAP", "notes": "UAE-based trading house, tiles + auto parts + housewares"})
    get_or_create(db, CustomerContact, customer_id=global_trading.id, name="Rashid Al Fahim",
                  defaults={"email": "rashid@alfahimtrading.ae", "phone": "+971-50-1234567"})

    horizon_auto, _ = get_or_create(db, Customer, name="Horizon Auto Parts Inc.",
                                     defaults={"account_owner": "Saurabh", "default_incoterm": "FOB", "notes": "US importer of aftermarket auto parts"})
    get_or_create(db, CustomerContact, customer_id=horizon_auto.id, name="Maria Chen",
                  defaults={"email": "maria.chen@horizonauto.com", "phone": "+1-213-555-0199"})

    db.commit()
    print("Seed complete.")
    print(f"Countries={db.query(Country).count()} Locations={db.query(Location).count()} "
          f"Carriers={db.query(Carrier).count()} Services={db.query(Service).count()} "
          f"HSCodes={db.query(HSCode).count()} TradeRules={db.query(TradeRule).count()} "
          f"RateCards={db.query(RateCard).count()} Customers={db.query(Customer).count()}")


if __name__ == "__main__":
    run()
