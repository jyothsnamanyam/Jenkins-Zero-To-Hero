"""Module holds configurations for all the accounts based on region and account type."""
import typing as t

DYNAMODB_TABLE_ACCOUNT_DATA = "NVSGISBSTGB-ONE-DESIGN-ACCOUNT-DATA"
DYNAMODB_TABLE_ONE_DESIGN = "NVSGISBSTGB-ONE-DESIGN-MIGRATION-DATA"
DYNAMODB_TABLE_PROPAGATE_DATA = "NVSGISBSTGB-ONE-DESIGN-PROPAGATE"

TGW_CONSTANTS: t.Dict[str, t.Any] = {
    "ap-northeast-1": {
        "short_region": "APJP",
        "one_tgw": "tgw-0325c591807fea123", # NVSGISBSTGB-EWTP-STGW-JP1A
        "bst_tgw": "tgw-06263fee8013487e6", # TGW-APJP-BST-01
        "dmz_tgw": "tgw-09d76e58e8cbbe83c", # TGWAPJPDMZ
        "resource_share_arn": "arn:aws:ram:ap-northeast-1:366103429990:resource-share/d7850ea4-1eca-49eb-a10e-ba9454f50579",
        "INTERNET": {
            "association": {
                "PGB": "tgw-rtb-089dcfd7fc176d25e",  # ONE-DESIGN-RTPRV-INTERCONNPGB01-ap-northeast-1
                "GB": "tgw-rtb-0e65f1aae9dabbebd",  # ONE-DESIGN-RTPRV-INTERCONNGB01-ap-northeast-1
                "DEV": "tgw-rtb-0a663270014c6fd10",  # ONE-DESIGN-RTPRV-INTERCONNDEV01-ap-northeast-1
            },
            "propagation": {
                "DEV": [
                    "tgw-rtb-03f393b42c6f7194b",  # ONE-DESIGN-RTPRV-EGRESS
                    "tgw-rtb-0d1b3fd78a809429a",  # ONE-DESIGN-RTPRV-INTERDMZGB01
                    "tgw-rtb-009ada0456c5f5f8c",  # ONE-DESIGN-RTPRV-INTERDMZNATDEV01
                    "tgw-rtb-0a663270014c6fd10",  # ONE-DESIGN-RTPRV-INTERCONNDEV01-ap-northeast-1
                ],
                "GB": [
                    "tgw-rtb-03f393b42c6f7194b",  # ONE-DESIGN-RTPRV-EGRESS
                    "tgw-rtb-0d1b3fd78a809429a",  # ONE-DESIGN-RTPRV-INTERDMZGB01
                    "tgw-rtb-066a0afe77c9940f8",  # ONE-DESIGN-RTPRV-INTERDMZNATGB01
                    "tgw-rtb-0e65f1aae9dabbebd",  # ONE-DESIGN-RTPRV-INTERCONNGB01-ap-northeast-1
                    "tgw-rtb-089dcfd7fc176d25e",  # ONE-DESIGN-RTPRV-INTERCONNPGB01-ap-northeast-1
                ],
                "PGB": [
                    "tgw-rtb-03f393b42c6f7194b",  # ONE-DESIGN-RTPRV-EGRESS
                    "tgw-rtb-0d1b3fd78a809429a",  # ONE-DESIGN-RTPRV-INTERDMZGB01
                    "tgw-rtb-022e4f37a86d19ca9",  # ONE-DESIGN-RTPRV-INTERDMZNATPGB01
                    "tgw-rtb-0e65f1aae9dabbebd",  # ONE-DESIGN-RTPRV-INTERCONNGB01-ap-northeast-1
                    "tgw-rtb-089dcfd7fc176d25e",  # ONE-DESIGN-RTPRV-INTERCONNPGB01-ap-northeast-1
                ]
            },
        },
        "ISOLATED": {
            "association": {
                "PGB": "tgw-rtb-033fa12993eda2122",  # ONE-DESIGN-RTPRV-INTERISOLPGB01
                "GB": "tgw-rtb-0986fe71c3243904d",  # ONE-DESIGN-RTPRV-INTERISOLGB01
                "DEV": "tgw-rtb-0b5219fd7ba572767",  # ONE-DESIGN-RTPRV-INTERISOLDEV01
            },
            "propagation": {
                "DEV": [
                    "tgw-rtb-0d1b3fd78a809429a",  # ONE-DESIGN-RTPRV-INTERDMZGB01
                    "tgw-rtb-009ada0456c5f5f8c",  # ONE-DESIGN-RTPRV-INTERDMZNATDEV01
                    "tgw-rtb-0b5219fd7ba572767",  # ONE-DESIGN-RTPRV-INTERISOLDEV01
                ],
                "GB": [
                    "tgw-rtb-0d1b3fd78a809429a",  # ONE-DESIGN-RTPRV-INTERDMZGB01
                    "tgw-rtb-066a0afe77c9940f8",  # ONE-DESIGN-RTPRV-INTERDMZNATGB01
                    "tgw-rtb-0986fe71c3243904d",  # ONE-DESIGN-RTPRV-INTERISOLGB01
                    "tgw-rtb-033fa12993eda2122"  # ONE-DESIGN-RTPRV-INTERISOLPGB01
                ],
                "PGB": [
                    "tgw-rtb-0d1b3fd78a809429a",  # ONE-DESIGN-RTPRV-INTERDMZGB01
                    "tgw-rtb-022e4f37a86d19ca9",  # ONE-DESIGN-RTPRV-INTERDMZNATPGB01
                    "tgw-rtb-0986fe71c3243904d",  # ONE-DESIGN-RTPRV-INTERISOLGB01
                    "tgw-rtb-033fa12993eda2122"  # ONE-DESIGN-RTPRV-INTERISOLPGB01
                ]
            },
        },
        "INTRANET": {
            "association": {
                "GB": "tgw-rtb-0ce54fb9d818f413f",  # ONE-DESIGN-RTPRV-INTRACONNGB01
                "PGB": "tgw-rtb-0ded42650d680ce75",  # ONE-DESIGN-RTPRV-INTRACONNPGB01
                "DEV": "tgw-rtb-0e5c938abb0ddd7e1",  # ONE-DESIGN-RTPRV-INTRACONNDEV01
                "SBX": "tgw-rtb-0e5c938abb0ddd7e1",  # ONE-DESIGN-RTPRV-INTRACONNDEV01
                "TST": "tgw-rtb-0e5c938abb0ddd7e1",  # ONE-DESIGN-RTPRV-INTRACONNDEV01
                "SHARED": "tgw-rtb-0c7d0c704f8ed9dcb",  # ONE-DESIGN-RTPRV-CONNSHAREDSERVGB01
                "DR": "tgw-rtb-0ce54fb9d818f413f",  # ONE-DESIGN-RTPRV-INTRACONNGB01
            },
            "propagation": {
                "GB": [
                    "tgw-rtb-03f393b42c6f7194b", # ONE-DESIGN-RTPRV-EGRESS
                    "tgw-rtb-0ce54fb9d818f413f",  # ONE-DESIGN-RTPRV-INTRACONNGB01
                    "tgw-rtb-0ded42650d680ce75",  # ONE-DESIGN-RTPRV-INTRACONNPGB01
                    "tgw-rtb-0c7d0c704f8ed9dcb",  # ONE-DESIGN-RTPRV-CONNSHAREDSERVGB01
                    "tgw-rtb-03e62f3148f37633b" # ONE-DESIGN-RTPRV-EWTPBSTVPN-DX-PHUB  
                ],
                "PGB": [
                    "tgw-rtb-03f393b42c6f7194b"  # ONE-DESIGN-RTPRV-EGRESS
                    "tgw-rtb-0ce54fb9d818f413f",  # ONE-DESIGN-RTPRV-INTRACONNGB01
                    "tgw-rtb-0ded42650d680ce75",  # ONE-DESIGN-RTPRV-INTRACONNPGB01
                    "tgw-rtb-0c7d0c704f8ed9dcb",  # ONE-DESIGN-RTPRV-CONNSHAREDSERVGB01
                    "tgw-rtb-03e62f3148f37633b" # ONE-DESIGN-RTPRV-EWTPBSTVPN-DX-PHUB  
                ],
                "DEV": [
                    "tgw-rtb-03f393b42c6f7194b", # ONE-DESIGN-RTPRV-EGRESS
                    "tgw-rtb-0e5c938abb0ddd7e1",  # ONE-DESIGN-RTPRV-INTRACONNDEV01
                    "tgw-rtb-0c7d0c704f8ed9dcb",  # ONE-DESIGN-RTPRV-CONNSHAREDSERVGB01
                    "tgw-rtb-03e62f3148f37633b" # ONE-DESIGN-RTPRV-EWTPBSTVPN-DX-PHUB  
                ],
                "SBX": [
                    "tgw-rtb-03f393b42c6f7194b", # ONE-DESIGN-RTPRV-EGRESS
                    "tgw-rtb-0c7d0c704f8ed9dcb",  # ONE-DESIGN-RTPRV-CONNSHAREDSERVGB01
                    "tgw-rtb-0e5c938abb0ddd7e1"  # ONE-DESIGN-RTPRV-INTRACONNDEV01 # Should be cross check with Senthil
                ],
                "TST": [
                    "tgw-rtb-03f393b42c6f7194b", # ONE-DESIGN-RTPRV-EGRESS
                    "tgw-rtb-0c7d0c704f8ed9dcb",  # ONE-DESIGN-RTPRV-CONNSHAREDSERVGB01
                    "tgw-rtb-0e5c938abb0ddd7e1"  # ONE-DESIGN-RTPRV-INTRACONNDEV01 # Should be cross check with Senthil
                ],
                "SHARED": [
                    "tgw-rtb-03f393b42c6f7194b" # ONE-DESIGN-RTPRV-EGRESS
                    "tgw-rtb-0ce54fb9d818f413f",  # ONE-DESIGN-RTPRV-INTRACONNGB01
                    "tgw-rtb-0ded42650d680ce75",  # ONE-DESIGN-RTPRV-INTRACONNPGB01
                    "tgw-rtb-0e5c938abb0ddd7e1",  # ONE-DESIGN-RTPRV-INTRACONNDEV01
                    "tgw-rtb-0c7d0c704f8ed9dcb",  # ONE-DESIGN-RTPRV-CONNSHAREDSERVGB01
                    "tgw-rtb-03e62f3148f37633b" # ONE-DESIGN-RTPRV-EWTPBSTVPN-DX-PHUB  
                ],
                "DR": [
                    "tgw-rtb-03f393b42c6f7194b" # ONE-DESIGN-RTPRV-EGRESS
                ],
            }
        },
        "DMZSPOKE": {
            "association": {
                "DMZ" : "tgw-rtb-0d1b3fd78a809429a",  # ONE-DESIGN-RTPRV-INTERDMZGB01
                "NATPGB": "tgw-rtb-022e4f37a86d19ca9",  # ONE-DESIGN-RTPRV-INTERDMZNATPGB01
                "NATGB": "tgw-rtb-066a0afe77c9940f8",  # ONE-DESIGN-RTPRV-INTERDMZNATGB01
                "NATDEV": "tgw-rtb-009ada0456c5f5f8c",  # ONE-DESIGN-RTPRV-INTERDMZNATDEV01
            },
            "propagation": {
                "DMZ": [
                    "tgw-rtb-089dcfd7fc176d25e",  # ONE-DESIGN-RTPRV-INTERCONNPGB01-ap-northeast-1
                    "tgw-rtb-0e65f1aae9dabbebd",  # ONE-DESIGN-RTPRV-INTERCONNGB01-ap-northeast-1
                    "tgw-rtb-0a663270014c6fd10",  # ONE-DESIGN-RTPRV-INTERCONNDEV01-ap-northeast-1
                    "tgw-rtb-033fa12993eda2122",  # ONE-DESIGN-RTPRV-INTERISOLPGB01
                    "tgw-rtb-0986fe71c3243904d",  # ONE-DESIGN-RTPRV-INTERISOLGB01
                    "tgw-rtb-0b5219fd7ba572767",  # ONE-DESIGN-RTPRV-INTERISOLDEV01
                    "tgw-rtb-03f393b42c6f7194b",  # ONE-DESIGN-RTPRV-EGRESS
                ]
            },
        },
        "NATVPCS_AWSPUBLICCIDRS" :{
            "prefixList_references": {
                "NATDEV": [
                    "tgw-rtb-0a663270014c6fd10",  # ONE-DESIGN-RTPRV-INTERCONNDEV01-ap-northeast-1
                    "tgw-rtb-0b5219fd7ba572767",  # ONE-DESIGN-RTPRV-INTERISOLDEV01
                ],
                "NATGB": [
                    "tgw-rtb-0e65f1aae9dabbebd",  # ONE-DESIGN-RTPRV-INTERCONNGB01-ap-northeast-1
                    "tgw-rtb-0986fe71c3243904d",  # ONE-DESIGN-RTPRV-INTERISOLGB01
                ],
                "NATPGB": [
                    "tgw-rtb-089dcfd7fc176d25e",  # ONE-DESIGN-RTPRV-INTERCONNPGB01-ap-northeast-1
                    "tgw-rtb-033fa12993eda2122",  # ONE-DESIGN-RTPRV-INTERISOLPGB01
                ]
            }
        }

    }
}

ON_PREM_CIDRS_ENTRIES=[
            {
                'Cidr': "10.0.0.0/8"
            },
            {
                'Cidr': "86.116.0.0/15"
            },
            {
                'Cidr': "147.167.0.0/16"
            },
            {
                'Cidr': "160.61.0.0/16"
            },
            {
                'Cidr': "160.62.0.0/16"
            },
            {
                'Cidr': "161.61.0.0/16"
            },
            {
                'Cidr': "162.86.0.0/16"
            },
            {
                'Cidr': "165.140.0.0/16"
            },
            {
                'Cidr': "170.60.0.0/16"
            },
            {
                'Cidr': "192.37.0.0/16"
            },
            {
                'Cidr': "202.236.224.0/21"
            },
            {
                'Cidr': "170.236.0.0/15"
            },
            {
                'Cidr': "172.16.0.0/12"
            },
            {
                'Cidr': "81.146.227.160/28"
            },
            {
                'Cidr': "109.159.241.160/28"
            }
        ]


SAME_CROSS_CIDRS_ENTRIES: t.Dict[str, t.Any] = {
    "ap-northeast-1": [
            {
                'Cidr': "10.242.0.0/16"
            },
            {
                'Cidr': "10.206.0.0/16"
            },
            {
                'Cidr': "10.206.244.0/22"
            },
            {
                'Cidr': "10.128.248.0/24"
            },
            {
                'Cidr': "10.33.0.0/19"
            },
            {
                'Cidr': "10.154.0.0/22"
            }
        ],
    "eu-west-1": []
}



DMZ_SAME_CIDRS_ENTRIES: t.Dict[str, t.Any] = {
    "ap-northeast-1": [
            {
                'Cidr': "10.37.0.0/16"
            },
            {
                'Cidr': "10.236.224.0/21"
            },
            {
                'Cidr': "10.236.0.0/15"
            },
            {
                'Cidr': "10.16.0.0/12"
            },
            {
                'Cidr': "10.146.227.160/28"
            },
            {
                'Cidr': "10.159.241.160/28"
            }
        ],
    "eu-west-1": []
}


AWS_CIDRS_ENTRIES: t.Dict[str, t.Any] = {
    "ap-northeast-1": [
        "13.34.69.64/27",
        "13.34.62.160/27",
        "15.221.34.0/24",
        "52.144.229.64/26",
        "13.248.70.0/24",
        "52.144.225.128/26",
        "13.34.53.192/27",
        "13.34.15.32/27",
        "104.255.59.82/32",
        "52.144.225.64/26",
        "52.219.68.0/22",
        "52.219.162.0/23",
        "52.93.127.239/32",
        "13.34.69.0/27",
        "52.219.16.0/22",
        "52.94.8.0/24",
        "99.77.56.0/21",
        "52.93.127.254/32",
        "52.93.127.177/32",
        "150.222.105.0/24",
        "13.34.53.160/27",
        "52.93.127.179/32",
        "15.230.152.0/24",
        "150.222.133.0/24",
        "52.93.127.174/32",
        "52.219.195.0/24",
        "13.34.46.192/27",
        "52.93.127.248/32",
        "52.93.121.195/32",
        "52.219.0.0/20",
        "15.221.152.0/24",
        "52.93.121.197/32",
        "54.239.0.80/28",
        "52.93.73.0/26",
        "52.95.34.0/24",
        "13.34.87.64/27",
        "52.93.250.0/23",
        "103.246.150.0/23",
        "54.240.225.0/24",
        "15.230.77.64/26",
        "150.222.141.0/24",
        "150.222.15.128/30",
        "99.82.170.0/24",
        "52.94.152.3/32",
        "13.34.0.160/27",
        "99.83.84.0/22",
        "52.93.127.253/32",
        "52.219.136.0/22",
        "13.34.0.128/27",
        "13.248.98.0/24",
        "52.93.121.189/32",
        "52.93.127.178/32",
        "52.93.127.147/32",
        "15.230.76.192/26",
        "15.230.77.0/26",
        "136.18.20.0/24",
        "52.93.127.246/32",
        "13.34.87.128/27",
        "52.219.201.0/24",
        "52.93.127.247/32",
        "52.93.121.196/32",
        "52.219.172.0/22",
        "13.34.15.0/27",
        "52.93.127.244/32",
        "52.219.200.0/24",
        "52.119.216.0/21",
        "13.34.69.96/27",
        "15.230.160.0/24",
        "52.93.121.187/32",
        "52.93.127.175/32",
        "15.230.59.0/24",
        "15.230.99.0/24",
        "52.93.127.255/32",
        "13.34.46.160/27",
        "13.34.87.160/27",
        "13.34.46.224/27",
        "150.222.91.0/24",
        "27.0.0.0/22",
        "52.93.121.188/32",
        "52.93.127.148/32",
        "52.93.127.250/32",
        "104.255.59.136/32",
        "13.34.46.128/27",
        "52.95.56.0/22",
        "104.255.59.83/32",
        "52.93.127.251/32",
        "13.34.58.192/27",
        "13.34.87.96/27",
        "52.93.245.0/24",
        "52.93.127.157/32",
        "52.93.121.198/32",
        "52.93.150.0/24",
        "52.93.127.249/32"
    ],
}