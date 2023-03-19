import dataclasses
import enum


class ChatGPTCommandType(enum.Enum):
    INITIALIZE = "initialize"
    GENERATE_SEQUENCE = "generate_sequence"


@dataclasses.dataclass
class ChatGPTConfig:
    model: str = "text-davinci-002-render-sha"
    _puid: str = "user-rxeR2OcR9TGEjrU2uNfeyNVN:1678927885-H4185EejI3o7f4gVpGFwmebml6%2BS5SlKYWoKSEhvLqE%3D"
    cf_clearance: str = "iSoyfpLAKq2Pg4aE6DScTH0GB0cpW1wEBM1mLSka1jM-1678842715-0-1-fe3f6a06.f2935554.1a1e2874-160"
    session_token: str = "eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..vhKUquD2detDzBqt.WnZF_7UUybc1Ol4ZtD8AU9mABpViEVyHsVB2nzrTcocGO7SSd_Kfmd2J4Nwo1S5tMweb11sWPRmBKDAVArn5EiAwBebqsdQUT2cPY4d4_0cTYii5R_wHJDVgK4LAP9T7ofi3PEpUZLld64d4XGGAhbLgUXKzW6gLIf7yivJkLIEdzwBAw4oKykQa43-G1_hK44WKt8bSEuFsSjsr5R3GMW8NGhLOzkDswIfFhnhMqjGqg2OvFMg2uphlmU853a6CgusHFRhPHtQGT_ZDsVwwiT4mvPsY7UQtjOKZSA5LELOMmJhkfPr-SkzG76sVUpbFh06DJPsIlYj0LOld8VJX0H1W_WSJ8A7qsm0_WgwwdTg07B8J5VnjfnpnA6pFkF6I6KTTezHNxXA7aM9GDuOrmnWUQvNANpTGmL--kBwUy59ZPE9IGa-vi9YytDEXCZMW-JufUu8RO2_Syx6xWVj7FStNk9f9e79rwtjflAhzWudA6QqXTeQt722RoSy3aQ49XevYQV-WJGPNUqo6dOYirFmee5mIyO2ntY6EFg-gYGB8vx7HJNGCTGt9IpXGGTF3_vF7s2GsLDob7KWEGNV9HqrkS7oLKKnysQGS8GrHfv-LUF61N-Ru9jLbQKfFEfWkWrpcdj4lwnX0F7ygqvP4rsZD5U-mjvthE7P1zLa5la5GBDokeguUDTGXE4LchYX3EzdVm6p18yP3Yn9xu5g0zKk5adpIxWLCASVUmCfI0rYA6SMc9lmSQNQwhtxuU1S2Ilvivkpf5zRHMNn1UTSHIciGBIF-hDqEK_qDvRkbnXcJBOzhmI4hi9lzPIiq62iDG1-9b5FmkySJF68ulEvYnwlp1y6p0meTc4xLGaDoy7jZvXTRxc2zr92CO1rpzsx3yHgzUPbvjnOcD63vAS33qzALV3TxLJV9LtxUl9VVrqO2V1n4sE65cTDP7XUvoJKIGqqRaaHG3thACPjaUq5cO22qFIUOOEGzPyc91pXTa685SxCE_FIv4sjNGESg7Mv4FH5DqeUroeQcn0MUtSad5rOe1KbhHxGqQ-FNkCFA3z5Ui_W1QbU8gRVeXn1-NZmvLJ20ONDTKdWtcpIE7P140LDkfdau_evQPitTkgdZCG1MhJ4_lUrLPwGYNYfIwlVwIqixriH7ZRIl7hVqqD2LTsbeQtV3x0L6dlgjzk9XJVdDK1xHhw9NCZWpAqTPL1pVUqZRfV-tW0Wzoh84wSIS-Yzem3k66_yrImRC9l45R1PLd9SyPhkNdnqeHOGqJQhi7f-P-VT-whxSBGzX9i4wUzQ_nLSKpGjYlAry-A6FgxeGDSqtAQsgCWB5xBRTxR0ZATyqKYZuGq1rywemKrIeK_JKEN5X7iyRJyB7PvGvxgw4REtZg1TSPuabzyb0DfxLvkin-LuJwbUAIa13Bv4WqUGg1WeD1UuJaj0VBvWiKPUwONjQ4xrvC3UHLxbNUy88vDF_8XKSIHOROMJr0Zx0_ZpoSUo1_o88pkj_BtVs0xXdtOjuh29xiJfDE2Yf6e4EULHp-ScW_oyHdfSPUxuKF_vPegAlgWh_fOjbXG60GpSeMPIpWWpeASx25OECjViufp0KKJb1Il9UM7Tc9pUiEn0YlYONCdJ1zXHlzroc9-PuHO17aeg_7EHrI8Mfss55r0SL--JJuQPNxc1URz2jm3XqzW5N_AQDEt5gdi1Xg8t5gUhdRKLQld27e_-Q4rNi5qfCiiDaUeyMDktdQyRznzUZFtaMYOSLtjtyYXCv74bVmLaOalgVPRcl2EUN5xOf3XfNb6G-DI1DMWqaxTa3WkZ_CIa4Ksa038NtyuDx7EVF_9atM5uZ3t_jygP3xFmlPE1xROsL9ook2G5_BQ8_n2VJLmG7Tewna-5MTWkjfub-bD0r65F-_L79ae2fJRwaEuFPIuBQn1ooOkss8n_vvZwEIcNbOv3uDN6FVXtyU9_OEImt-iZCShRu5ZnxnTRf2uZKgl1W3JEx3DL6vMt96gx777nBs6knjylomfjEHR6SYokkoe5HthfwG7Q1yYmYUFmBhBqY5pUVaiJ9gMoV_Yxjzh09rp-wxck9fkuJ32HY-3xcGzEf3srvQPIhqk5gzqEhUnQkH4-fHTt_zusbVsfjE89ZRbdG3EQQS-7XeEvmAu_1norrw0Zblkpjpo7_jmpUxTTbLZFXQ31Q0BR_nc8usjnEoJLJpODrHVh7Xr0ArWxwRTjHQBq8rFFAFiCNhRV5VBCXisl7-YL_bk8F3fSzUG2dOgI18w0d3exlyw7xKWQjmaSxO9f-eA5yxEzWa7dR6wXKmkchP4IZY4ykE8O95nIMg2n2VvDbeqogu2QKmewCj6pJAXfNfT-XtMnK1oNjFPZVHAw5D3gT3QxfeXhi-JkLvFe8EoTHim0IiQVsi144-z8Mw9nF0heXci2gNdJVJvv3CFKCNh16chZWbH-duOXJhLZf-3rE4TYyCTM7BA.4HxTqdNvAuICUU7JMSRn3w"
    error_wait_time: float = 20
    is_debugging: bool = False
