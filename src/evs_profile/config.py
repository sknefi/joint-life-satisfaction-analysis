"""Documented codes and variable metadata used by the profiler."""

from __future__ import annotations

from dataclasses import dataclass


MISSING_CODES = {
    "-1": "Don't know",
    "-2": "No answer",
    "-3": "Not applicable",
    "-4": "Not asked in survey",
    "-5": "Missing: Other",
}

STUDY_LABELS = {"1": "EVS", "2": "WVS"}
STUDY_OPTIONS = {"EVS": "1", "WVS": "2", "all": None}

MODE_LABELS = {
    "1": "Computer-Assisted Personal Interviewing (CAPI)",
    "2": "Paper-and-Pencil Interviewing (PAPI)",
    "3": "Computer-Assisted Web Interviewing (CAWI)",
    "4": "Mail/Post",
    "5": "Computer-Assisted Telephone Interviewing (CATI)",
    "6": "Web-based interview",
}

COUNTRY_NAMES = {
    "AD": "Andorra",
    "AL": "Albania",
    "AM": "Armenia",
    "AR": "Argentina",
    "AT": "Austria",
    "AU": "Australia",
    "AZ": "Azerbaijan",
    "BA": "Bosnia and Herzegovina",
    "BD": "Bangladesh",
    "BG": "Bulgaria",
    "BO": "Bolivia",
    "BR": "Brazil",
    "BY": "Belarus",
    "CA": "Canada",
    "CH": "Switzerland",
    "CL": "Chile",
    "CN": "China",
    "CO": "Colombia",
    "CY": "Cyprus",
    "CZ": "Czechia",
    "DE": "Germany",
    "DK": "Denmark",
    "EC": "Ecuador",
    "EE": "Estonia",
    "EG": "Egypt",
    "ES": "Spain",
    "ET": "Ethiopia",
    "FI": "Finland",
    "FR": "France",
    "GB": "Great Britain",
    "GE": "Georgia",
    "GR": "Greece",
    "GT": "Guatemala",
    "HK": "Hong Kong SAR",
    "HR": "Croatia",
    "HU": "Hungary",
    "ID": "Indonesia",
    "IN": "India",
    "IQ": "Iraq",
    "IR": "Iran",
    "IS": "Iceland",
    "IT": "Italy",
    "JO": "Jordan",
    "JP": "Japan",
    "KE": "Kenya",
    "KG": "Kyrgyzstan",
    "KR": "South Korea",
    "KZ": "Kazakhstan",
    "LB": "Lebanon",
    "LT": "Lithuania",
    "LV": "Latvia",
    "LY": "Libya",
    "MA": "Morocco",
    "ME": "Montenegro",
    "MK": "North Macedonia",
    "MM": "Myanmar",
    "MN": "Mongolia",
    "MO": "Macau SAR",
    "MV": "Maldives",
    "MX": "Mexico",
    "MY": "Malaysia",
    "NG": "Nigeria",
    "NI": "Nicaragua",
    "NIR": "Northern Ireland",
    "NL": "Netherlands",
    "NO": "Norway",
    "NZ": "New Zealand",
    "PE": "Peru",
    "PH": "Philippines",
    "PK": "Pakistan",
    "PL": "Poland",
    "PR": "Puerto Rico",
    "PT": "Portugal",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "SE": "Sweden",
    "SG": "Singapore",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "TH": "Thailand",
    "TJ": "Tajikistan",
    "TN": "Tunisia",
    "TR": "Turkey",
    "TW": "Taiwan ROC",
    "UA": "Ukraine",
    "US": "United States",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "VE": "Venezuela",
    "VN": "Vietnam",
    "ZW": "Zimbabwe",
}


@dataclass(frozen=True)
class VariableDefinition:
    label: str
    statistical_type: str
    valid_min: int | None = None
    valid_max: int | None = None
    note: str = ""


KEY_VARIABLES: dict[str, VariableDefinition] = {
    "A170": VariableDefinition(
        "Satisfaction with your life",
        "Ordinal, bounded 1-10 (candidate Y)",
        1,
        10,
        "Treating this as continuous is a modelling assumption.",
    ),
    "A008": VariableDefinition("Feeling of happiness", "Ordinal categorical", 1, 4),
    "A009": VariableDefinition("Subjective state of health", "Ordinal categorical", 1, 5),
    "A165": VariableDefinition("Most people can be trusted", "Binary categorical", 1, 2),
    "A173": VariableDefinition(
        "Freedom of choice and control", "Ordinal, bounded 1-10", 1, 10
    ),
    "X001": VariableDefinition("Sex", "Nominal categorical", 1, 2),
    "X003": VariableDefinition(
        "Age", "Integer; upper-censored/top-coded", 16, 82, "82 means 82 or older."
    ),
    "X007": VariableDefinition("Marital status", "Nominal categorical", 1, 6),
    "X011": VariableDefinition(
        "Number of children", "Capped count", 0, 5, "5 means 5 or more children."
    ),
    "X013": VariableDefinition(
        "Number of people in household",
        "Capped count",
        1,
        6,
        "6 means 6 or more people.",
    ),
    "X025A_01": VariableDefinition(
        "Highest education attained (ISCED)", "Ordinal categorical", 0, 8
    ),
    "X025R": VariableDefinition("Recoded educational level", "Ordinal categorical", 1, 3),
    "X028": VariableDefinition("Employment status", "Nominal categorical", 1, 8),
    "X047_WVS7": VariableDefinition(
        "WVS7 income scale",
        "Ordinal, source-specific",
        1,
        10,
        "Subjective position from the lowest to highest income group in the country.",
    ),
    "X047E_EVS5": VariableDefinition(
        "EVS5 income scale",
        "Ordinal, source-specific",
        1,
        10,
        "Net household-income deciles; do not automatically merge with X047_WVS7.",
    ),
}

WEIGHT_VARIABLES = ("gwght", "pwght", "wght_eq1000")
TOP_CODED_VARIABLES = {"X003": "82", "X011": "5", "X013": "6"}

