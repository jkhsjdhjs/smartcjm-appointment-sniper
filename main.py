import argparse
import datetime
import itertools
import logging
import json
import urllib.parse
import time
import zoneinfo

from bs4 import BeautifulSoup
import requests


parser = argparse.ArgumentParser(description="Get an appointment in a SmartCJM calendar effortlessly!",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument("-b", "--base-url", type=str,
                    default="https://stadt-aachen.saas.smartcjm.com/m/buergerservice/extern/calendar",
                    help="the base URL to use with SmartCJM calendars other than Aachen Bürgerservice")
parser.add_argument("-c", "--calendar-uid", type=str, default="15940648-b483-46d9-819e-285707f1fc34",
                    help="the UID of the calendar. specify when attempting to book service types outside "
                         "the regular calendar, or for other services than Aachen Bürgerservice")
parser.add_argument("-n", "--dry-run", action="store_true", help="run the program as usual, "
                    "but don't register any appointment")
parser.add_argument("-y", "--no-confirm", action="store_true", help="don't confirm anything, always assume 'yes'. "
                    "useful when running this tool as a service")
parser.add_argument("--log-level", default="INFO", choices=logging.getLevelNamesMapping().keys(),
                    help="Set the logging level")

subparsers = parser.add_subparsers(required=True, dest="subcommand",
                                   help="(see --help of the subcommands for further parameters)")

subparsers.add_parser("list", help="list available appointment types and their UID",
                      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser_book = subparsers.add_parser("book", help="book an appointment given the parameters",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser_book.add_argument("-u", "--uid", required=True, help="the UID of the appointment type to snipe "
                         "(retrieve via the `list` subcommand)")
parser_book.add_argument("-m", "--mail", required=True, type=str,
                         help="the mail address for booking the appointment")
parser_book.add_argument("-l", "--location", required=True, type=str,
                         help="the location where you want to have your appointment. "
                         "the location is selected via substring, so every location that this value is "
                         "a case-insensitive substring of will be considered")
parser_book.add_argument("--time-from", required=True, type=datetime.datetime.fromisoformat,
                         help="earliest datetime you want to have your appointment. ISOformat - YYYY-MM-DD:HH:mm:ss")
parser_book.add_argument("--time-to", required=True, type=datetime.datetime.fromisoformat,
                         help="latest datetime you want to have your appointment. ISOformat - YYYY-MM-DD:HH:mm:ss")
parser_book.add_argument("-s", "--sleep", default=30, type=int, help="how long to wait between attempts (in seconds)")

args = parser.parse_args()

logging.basicConfig(level=args.log_level, format="%(asctime)s - %(levelname)s - %(module)s - %(message)s")
log = logging.getLogger(__name__)

URL_SERVICE_LIST = f"{args.base_url}/get_service_list"
URL_SEARCH_RESULT = f"{args.base_url}/search_result"
URL_BOOKING = f"{args.base_url}/booking"

if args.subcommand == "list":
    r = requests.get(URL_SERVICE_LIST, params={"uid": args.calendar_uid})
    assert r.ok
    res = r.json()
    assert res["success"]
    categories: dict[str, list[int]] = {}
    services = res["results"]
    for idx, service in enumerate(services):
        try:
            category_name = service["categories"][0]["display_name"].strip()
        except IndexError:
            category_name = "Sonstiges"
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append(idx)
    first_iter: bool = True
    for category, indices in sorted(categories.items(), key=lambda s: s[0].upper()):
        # print blank line as a separator between categories
        if first_iter:
            first_iter = False
        else:
            print()
        print(category)
        for idx in indices:
            print(services[idx]["uid"], services[idx]["service_name"])
    exit()

if args.time_from.tzinfo is None:
    log.warning("The datetime supplied for time-from has no timezone, assuming Europe/Berlin")
    args.time_from = args.time_from.replace(tzinfo=zoneinfo.ZoneInfo("Europe/Berlin"))

if args.time_to.tzinfo is None:
    log.warning("The datetime supplied for time-to has no timezone, assuming Europe/Berlin")
    args.time_to = args.time_to.replace(tzinfo=zoneinfo.ZoneInfo("Europe/Berlin"))

if not args.no_confirm:
    print(f"This tool will check for appointments on location '{args.location}' between {args.time_from} "
          "and {args.time_to}.")
    if not args.dry_run:
        print(f"This tool will also book a matching appointment for the mail address '{args.mail}'.")
    user_input = input("Is this correct? [y/N] ").strip().lower()
    if user_input not in ["y", "n", ""]:
        exit(1)
    if user_input != "y":
        exit()

for i in itertools.count(1):
    if i >= 2:
        log.info(f"sleeping for {args.sleep}s")
        time.sleep(args.sleep)

    log.info(f"checking for available appointments, try #{i}")

    # apparently we don't even need a requests.Session() for storing cookies
    s = requests

    log.debug("requesting CSRF token and WSID")

    # get CSRF token and WSID (WSID is probably some kind of session id)
    res = s.get(args.base_url, params={"uid": args.calendar_uid})
    assert res.ok

    wsid = urllib.parse.parse_qs(urllib.parse.urlparse(res.url).query)["wsid"]

    soup = BeautifulSoup(res.text, "html.parser")

    csrf_elem = soup.find(id="RequestVerificationToken")

    log.debug("submitting wanted appointments")

    res = s.post(args.base_url, params={
            "uid": args.calendar_uid,
            "wsid": wsid
        },
        data={
            csrf_elem["name"]: csrf_elem["value"],
            "services": args.uid,
            f"service_{args.uid}_amount": 1
        }
    )
    assert res.ok

    log.debug("requesting appointment list")

    res = s.get(URL_SEARCH_RESULT, params={"uid": args.calendar_uid, "wsid": wsid})
    assert res.ok

    soup = BeautifulSoup(res.text, "html.parser")
    appointments = json.loads(soup.find(id="json_appointment_list").text)["appointments"]
    if appointments == "nothing_Found":
        log.info("no appointments available")
        continue
    assert isinstance(appointments, list)

    for a in appointments:
        a_location, a_date = a["unit"].strip(), datetime.datetime.fromisoformat(a['datetime_iso86001'])
        if args.location.lower() not in a_location.lower():
            log.debug(f"rejecting appointment {a_date} {a_location} due to unwanted location")
            continue
        if a_date < args.time_from or a_date > args.time_to:
            log.debug(f"rejecting appointment {a_date} {a_location} due to timeframe mismatch")
            continue

        # book appointment
        log.info(f"selected appointment on {a_date} at {a_location}")

        if args.dry_run:
            log.info(f"skipping booking")
            exit()

        # get CSRF token again...
        res = s.get(URL_BOOKING, params={
            "uid": args.calendar_uid,
            "wsid": wsid,
            "appointment_datetime": a_date.isoformat(),
            "location": a["unit_uid"],
        })
        assert res.ok
        soup = BeautifulSoup(res.text, "html.parser")
        csrf_elem = soup.find(id="RequestVerificationToken")

        s.post(URL_BOOKING, params={
                "uid": args.calendar_uid,
                "wsid": wsid,
                "appointment_datetime": a_date.isoformat(),
                "location": a["unit_uid"]
            },
            data={
                csrf_elem["name"]: csrf_elem["value"],
                "mail": args.mail
            }
        )
        assert res.ok
        log.info(f"booked the appointment! check your mails :)")
        exit()
    log.info("no matching appointments available")
