import requests
from bs4 import BeautifulSoup as bs
from schedulit_utils import headers, POČETAK_SEMESTRA, KRAJ_SEMESTRA, DVORANE
from datetime import timedelta
from dateutil.parser import parser


class InvalidLogin(Exception):
    pass


class AvailabilityUndeterminable(Exception):
    pass


cookies = None
memberid = None

dani = "ned,pon,uto,sri,čet,pet,sub".split(',')


def login(username, password):
    global cookies, memberid
    start = requests.get("http://arhiva.fet.unipu.hr/rezervacije",
                         headers=headers)
    cookies = start.cookies
    cookies.set("lang", "en_US", domain='arhiva.fet.unipu.hr')
    result = requests.post("http://arhiva.fet.unipu.hr/rezervacije/index.php",
                           headers=headers,
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
                          headers=headers,
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
    def __init__(self, dvorana, dan, početak, kraj, opis):
        self.dvorana = dvorana
        self.machid = DVORANE[dvorana]
        try:
            dan = int(dan)
        except ValueError:
            if dan.lower() in dani:
                dan = dani.index(dan)
            else:
                raise ValueError("Nepoznati dan")

        self.dan = POČETAK_SEMESTRA + timedelta(dan-1)
        self.dan_u_tjednu = dan
        self.opis = opis
        self.početak = parser().parse(početak).time()
        self.starttime = self.početak.hour * 60 + self.početak.minute
        self.kraj = parser().parse(kraj).time()
        self.endtime = self.kraj.hour * 60 + self.kraj.minute

    def slobodno(self):
        dan = self.dan.strftime("%m/%d/%Y")
        data = dict(start_date=dan,
                    end_date=dan,
                    starttime=self.starttime,
                    endtime=self.endtime,
                    frequency=1,
                    interval="week",
                    repeat_until=KRAJ_SEMESTRA.strftime("%m/%d/%Y"),
                    week_number=1,
                    repeat_day=[self.dan_u_tjednu],
                    machid=self.machid,
                    scheduleid="sc149ae50fcaca66")
        check = requests.post("http://arhiva.fet.unipu.hr/rezervacije/"
                              "check.php",
                              headers=headers,
                              cookies=cookies,
                              data=data)
        result = bs(check.content, 'html.parser')
        info = result.find("tr").attrs["class"]
        if 'messagePositive' in info:
            return True
        elif 'messageNegative' in info:
            return False
        else:
            raise AvailabilityUndeterminable("Huh?!")

    def rezerviraj(self):
        dan = self.dan.strftime("%m/%d/%Y")
        data = dict(start_date=dan,
                    end_date=dan,
                    starttime=self.starttime,
                    endtime=self.endtime,
                    frequency=1,
                    interval="week",
                    repeat_until=KRAJ_SEMESTRA.strftime("%m/%d/%Y"),
                    week_number=1,
                    repeat_day=[self.dan_u_tjednu],
                    machid=self.machid,
                    scheduleid="sc149ae50fcaca66",
                    summary=self.opis,
                    fn="create",
                    pending=0,
                    btnSubmit="Save",
                    memberid=memberid)
        hdr = headers.copy()
        hdr["Referer"] = "http://arhiva.fet.unipu.hr/rezervacije/reserve.php"
        reserve = requests.post("http://arhiva.fet.unipu.hr/rezervacije/"
                                "reserve.php",
                                headers=hdr,
                                cookies=cookies,
                                data=data)
        return b'successfully' in reserve.content

    def __str__(self):
        dan = dani[self.dan_u_tjednu]
        return (f"Termin: {self.dvorana} ({dan}, "
                "{self.početak}--{self.kraj}) {self.opis}")
