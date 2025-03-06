# SmartCJM Appointment Sniper
A small python script to book appointments at your local Bürgerservice effortlessly, since at least Bürgerservice Aachen is notorious for not having any appointments available, except for a few minutes every day.
The script checks for available appointments at a set interval and automatically books an appointment once one matching your preferences becomes available.


## Installation
```
$ python -m venv venv
$ . venv/bin/activate
$ pip install -r requirements.txt
```


## Usage
First you need to know what type of appointment you want to book.
You can list all available appointment types via:
```
$ python main.py list
Ausweise / Reisepässe - Wohnsitz im Ausland
d1a00eaf-f73b-4e98-ac2f-568b2d9c16c1 Erstellung Biometrisches Foto (Wohnsitz Ausland) 
4a561c29-1721-4e27-b470-1a3265bf93ab Ausweis: Beantragung (Personen unter 16 Jahren, Wohnsitz Ausland) 
[...]
```

The first column contains the UID of the appointment, pick one and memorize it as it is required for running the actual script.
It can be executed as follows:
```
$ python main.py book -u <the-UID-you-memorized> -l <location> --time-from 2025-03-06T08:00:00+01:00 --time-to 2025-03-06T15:00:00+01:00 -m <your-mail-address>
```
The location is checked via a simple case-insensitive substring check, so appointments whose location does not contain your specified location are not booked.
`time-from` and `time-end` limit the time range, any appointment not in this range is rejected and will not be booked.

For further information check:
```
$ python main.py --help
$ python main.py list --help
$ python main.py book --help
```

Happy booking :)
```
$ python main.py book -u 7bee4872-ba56-4070-9f6d-f45afdf491cb -l katschhof --time-from 2025-03-06T08:00:00+01:00 --time-to 2025-03-06T15:00:00+01:00 -m mail@example.com
This tool will check for appointments on location 'katschhof' between 2025-03-06 08:00:00+01:00 and 2025-03-06 15:00:00+01:00.
This tool will also book a matching appointment for the mail address 'mail@example.com'.
Is this correct? [y/N] y
2025-03-05 14:12:05,030 - INFO - main - checking for available appointments, try #1
2025-03-05 14:12:05,911 - INFO - main - no appointments available
2025-03-05 14:12:05,911 - INFO - main - sleeping 30s
[...]
2025-03-05 23:24:30,858 - INFO - main - sleeping 30s
2025-03-05 23:25:00,858 - INFO - main - checking for available appointments, try #1063
2025-03-05 23:25:02,478 - INFO - main - selected appointment on 2025-03-06 09:10:00+01:00 at Bürgerservice Katschhof
2025-03-05 23:25:03,131 - INFO - main - booked the appointment! check your mails :)
```


## FAQ

### Why do I only need to enter my mail address? What about my name and date of birth, like the website requires?
While the webform requires additional data, the service doesn't perform any server-side validation, so I don't see a point in sending more data than necessary.
You don't even have to accept their privacy policy, whether you accept it or not is also not validated on the server.

### How can I use this tool with SmartCJM systems other than Aachen Bürgerservice?
You can use the `--base-url` and `--calendar-uid` flags to make it work with a different SmartCJM system.
The calendar UID can be extracted from the `uid` query parameter, e.g. if your booking URL looks like this:
```
https://stadt-aachen.saas.smartcjm.com/m/buergerservice/extern/calendar/?uid=15940648-b483-46d9-819e-285707f1fc34
```

Your **base URL** and **calendar UID** would be:
```
BASE URL: https://stadt-aachen.saas.smartcjm.com/m/buergerservice/extern/calendar
UID: 15940648-b483-46d9-819e-285707f1fc34
```


## Related Projects
- https://github.com/noworneverev/aachen-termin-bot  
  Appointment scraping only, no automatic booking.
  Doesn't seem to work anymore, no messages are being posted to the telegram channels for the different months.
- https://github.com/larsborn/smart-cjm-scraper  
  Appointment scraping only, no automatic booking.
  Didn't test it, but the code looks more organized than mine :D


## License
<img align="right" src="https://www.gnu.org/graphics/gplv3-127x51.png"/>

This project is licensed under the GNU General Public License v3.0, see [LICENSE](LICENSE).
