from typing import List
import requests

from constants import BASE_URL, USER_AGENT

from pydantic import BaseModel, computed_field


class ReservationSlot(BaseModel):
    wdt: str | None = None
    wyoil: str | None = None
    wtime: str | None = None
    CD_COMPANY: str | None = None
    BRANCH_CD: str | None = None
    CD_HALL: str | None = None
    WEDDING_DT: str | None = None
    CD_TIME: str | None = None
    BRANCH_NM: str | None = None
    HALL_NM: str | None = None
    W_DT: str | None = None
    W_YOIL: str | None = None
    YOIL_NO: str | None = None
    W_TIME: str | None = None
    RENT_AMT: str | None = None
    RENT_DC: str | None = None
    EAT_AMT: str | None = None
    EAT_DC: str | None = None
    PER_CNT: str | None = None
    PER_DC: str | None = None
    JJIM: str | None = None
    BRANCH_LOC: str | None = None
    HALL_CD: str | None = None
    BRANCH_IMG_CD: str | None = None
    HALL_IMG_CD: str
    ID_YN: str | None = None
    TOT_AMT: str | None = None
    EAT_DANGA: str | None = None
    TEXT_PROMOTION_SMART: str | None = None

    @computed_field
    @property
    def name(self) -> str:
        w_month = self.WEDDING_DT[4:6]
        w_day = self.WEDDING_DT[6:8]
        w_weekday = self.W_YOIL[0]
        w_time = self.W_TIME
        hall_nm = self.HALL_NM
        return f"{w_month}/{w_day}({w_weekday}) {w_time} {hall_nm}"

    @computed_field
    @property
    def price(self) -> str:
        try:
            rent_dc = int(self.RENT_DC)
            eat_dc = int(self.EAT_DC)
            per_dc = int(self.PER_DC)
            price = int(eat_dc / per_dc)

            def manwon(value: int, prec: int) -> str:
                return f"{value / 10000:,.{prec}f}"

            return f"{manwon(rent_dc, 0)} {manwon(price, 1)} {per_dc}"
        except Exception as e:
            return f"ERROR_PRICE {e}"


class ApelClient:
    def __init__(self):
        self.username = None
        self.access_token = None

    def login(self, username: str, password: str):
        headers = {
            "accept": "*/*",
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json",
            "origin": "https://apelgamo.com",
            "priority": "u=1, i",
            "referer": "https://apelgamo.com/",
            "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": USER_AGENT,
        }
        params = {
            "username": username,
            "password": password,
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/user/login",
            headers=headers,
            json=params,
        )
        if response.status_code != 200:
            raise ValueError(
                f"Failed to login: status_code={response.status_code} text={response.text}"
            )

        try:
            r_json = response.json()
            grant_type = r_json.get("data", {}).get("jwtToken", {}).get("grantType")
            access_token = r_json.get("data", {}).get("jwtToken", {}).get("accessToken")
        except Exception as e:
            raise ValueError(f"Failed to login: {e} {response.text}")

        if access_token is None or grant_type is None:
            raise ValueError(f"Failed to login: {r_json}")

        self.username = username
        self.access_token = f"{grant_type} {access_token}"

        print("Login success")

    def search(
        self,
        brand: str,
        branch: str,
        hall: str,
        st_dt: str,
        ed_dt: str,
        time: str,
        yoil: str,
    ):
        headers = {
            "User-Agent": USER_AGENT,
            "accept": "*/*",
            # "authorization": self.access_token,
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json",
            "origin": "https://apelgamo.com",
            "priority": "u=1, i",
            "referer": "https://apelgamo.com/",
            "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
        }
        params = {
            # "id": self.username,
            # "accessToken": self.access_token,
            "brand": brand,
            "branch": branch,
            "hall": hall,
            "st_dt": st_dt,
            "ed_dt": ed_dt,
            "time": time,
            "yoil": yoil,
            "min_deposit": "100",
            "max_deposit": "400",
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/wedding/rsv_slot",
            headers=headers,
            json=params,
        )

        slots: List[ReservationSlot] = []
        try:
            r_json = response.json()
            data_list = r_json["data"]
            for item in data_list:
                r_model = ReservationSlot.model_validate(item)
                slots.append(r_model)
        except Exception as e:
            raise ValueError(f"Failed to search: {e} {response.text}")

        print(f"Search success - {len(slots)} slots")

        return slots
