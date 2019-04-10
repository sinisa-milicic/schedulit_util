import requests
from bs4 import BeautifulSoup as bs
from schedulit_utils import HEADERS, POČETAK_SEMESTRA, DVORANE
from datetime import timedelta
from dateutil.parser import parser


class InvalidLogin(Exception):
    pass


class AvailabilityUndeterminable(Exception):
    pass


cookies = None
memberid = None

dani = "pon,uto,sri,čet,pet,sub,ned".split(',')


def login(username, password):
    global cookies, memberid
    start = requests.get("http://arhiva.fet.unipu.hr/rezervacije",
                         headers=HEADERS)
    cookies = start.cookies
    cookies.set("lang", "en_US", domain='arhiva.fet.unipu.hr')
    result = requests.post("http://arhiva.fet.unipu.hr/rezervacije/index.php",
                           headers=HEADERS,
                           cookies=cookies,
                           data=dict(email=username,
                                     password=password,
                                     language="en_US",
                                     login="Log+In",
                                     resume=""))
    if result.content:
        cookies = None
        memberid = None
        raise InvalidLogin("Error logging in to phpSchedulit")
    result = requests.get("http://arhiva.fet.unipu.hr/rezervacije/ctrlpnl.php",
                          headers=HEADERS,
                          cookies=cookies,
                          data=dict(email=username,
                                    password=password,
                                    language="en_US",
                                    login="Log+In",
                                    resume=""))
    idx = result.content.find(b"rss.php?id=")
    idx += 11
    slice_len = result.content[idx:].find(b'"')
    memberid = result.content[idx:idx+slice_len].decode("utf8")


class Termin:
    def __init__(self, dvorana, dan, vrijeme_početka, kraj, opis, tjedana=15,
                 polazni_tjedan=POČETAK_SEMESTRA):
        self.dvorana = dvorana
        self.machid = DVORANE[dvorana]
        try:
            dan = int(dan)
        except ValueError:
            if dan.lower() in dani:
                dan = dani.index(dan.lower())
            else:
                raise ValueError("Nepoznati dan")

        self.polazni_dan = polazni_tjedan \
            + timedelta(dan-polazni_tjedan.weekday())
        self.završni_dan = self.polazni_dan+timedelta(tjedana*7)
        self.dan_u_tjednu = dan + 1
        self.opis = opis
        self.vrijeme_početka = parser().parse(vrijeme_početka).time()
        self.starttime = self.vrijeme_početka.hour * 60 \
            + self.vrijeme_početka.minute
        self.kraj = parser().parse(kraj).time()
        self.endtime = self.kraj.hour * 60 + self.kraj.minute
        self.compute_data()

    def compute_data(self):
        polazni_dan = self.polazni_dan.strftime("%m/%d/%Y")
        završni_dan = (self.završni_dan+timedelta(1)).strftime("%m/%d/%Y")
        self.check_data = dict(start_date=polazni_dan,
                               end_date=polazni_dan,
                               starttime=self.starttime,
                               endtime=self.endtime,
                               frequency=1,
                               interval="week",
                               repeat_until=završni_dan,
                               week_number=1,
                               repeat_day=[self.dan_u_tjednu],
                               machid=self.machid,
                               scheduleid="sc149ae50fcaca66")

        self.rezerviraj_data = self.check_data.copy()
        self.rezerviraj_data.update(dict(summary=self.opis,
                                         fn="create",
                                         pending=0,
                                         btnSubmit="Save"))

    def slobodno(self):
        self.compute_data()
        check = requests.post("http://arhiva.fet.unipu.hr/rezervacije/"
                              "check.php",
                              headers=HEADERS,
                              cookies=cookies,
                              data=self.check_data)
        result = bs(check.content, 'html.parser')
        info = result.find("tr").attrs["class"]
        if 'messagePositive' in info:
            return True
        elif 'messageNegative' in info:
            return False
        else:
            raise AvailabilityUndeterminable("Huh?!")

    def rezerviraj(self):
        self.compute_data()
        hdr = HEADERS.copy()
        hdr["Referer"] = "http://arhiva.fet.unipu.hr/rezervacije/reserve.php"
        reserve = requests.post("http://arhiva.fet.unipu.hr/rezervacije/"
                                "reserve.php",
                                headers=hdr,
                                cookies=cookies,
                                data=self.rezerviraj_data)
        print(reserve.content)
        return b'successfully' in reserve.content

    def __str__(self):
        dan = dani[self.dan_u_tjednu]
        return (f"Termin: {self.dvorana} ({dan}, "
                f"{self.vrijeme_početka}--{self.kraj}) {self.opis}")
