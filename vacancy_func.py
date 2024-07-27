import re
import os

import requests
import pandas as pd
import matplotlib.pyplot as plt
import folium
from itertools import chain
from bs4 import BeautifulSoup
from collections import Counter
from datetime import date, datetime
from fake_useragent import UserAgent
from geopy.geocoders import Nominatim


def get_all_vacancies(vacancies, exp="noExperience", page=0, search_period=0):
    """
    Get all vacancies with the specified experience level and start page number.
    Args:
        vacancies (list): list of vacancies to search for.
        exp (str): experience level, default is 'noExperience'.
        page (int): page number to start the search, default is 0.
    Returns:
        pd.DataFrame: DataFrame containing the ids of all vacancies found.
    """
    request_text = "+or+".join(["%22" + i.replace(" ", "+") + "%22" for i in vacancies])

    all_vacancies_ids = []
    df = pd.DataFrame(columns=["id", "vacancy_name"])

    def save_data(all_vacancies_ids):
        """
        Save the collected data of vacancies.
        Args:
            all_vacancies_ids (list): list of vacancy ids.
        Returns:
            pd.DataFrame: appended DataFrame with id columns.
        """
        data = pd.DataFrame(zip(all_vacancies_ids), columns=["id"])
        all_vacancies_ids = []
        return df.append(data)

    def get_current_vacancies_id(soup):
        """
        Get the ids of the current vacancies from the parsed HTML soup.
        Args:
            soup: parsed HTML soup object.
        Returns:
            list: list of vacancy ids.
        """
        page_links = soup.find_all(
            "a",
            attrs={
                "class": "bloko-link",
                "target": "_blank",
                "href": re.compile(r"https:\/\/perm.hh.ru\/"),
            },
        )
        pattern = r"[a-zA-Z:\/.]*([0-9]*)\?"
        vacancies_id = [re.findall(pattern, link["href"]) for link in page_links]
        return list(chain(*vacancies_id))

    while True:
        if page % 10 == 0:
            print(f"current page = {page}")

        url = f"https://hh.ru/search/vacancy?text={request_text}&search_period={search_period}\
                &items_on_page=15&area=113&experience={exp}&page={page}"
        headers = {"User-Agent": UserAgent().random}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("Error", response.status_code)
            df = save_data(all_vacancies_ids)
            return df
        soup = BeautifulSoup(response.text)
        current_vacancies_ids = get_current_vacancies_id(soup)
        if not current_vacancies_ids:
            df = save_data(all_vacancies_ids)
            return df

        all_vacancies_ids.extend(current_vacancies_ids)
        page += 1


def get_vacancy_info(vacancies_id):
    """
    Get details of vacancies based on the provided vacancy IDs.
    Args:
        vacancies_id (list): list of vacancy IDs to fetch details for.
    Returns:
        pd.DataFrame: DataFrame containing information about the vacancies.
    """
    counter = 0
    df = pd.DataFrame(
        columns=[
            "id",
            "vacancy_name",
            "experience",
            "work_type",
            "busyness",
            "city",
            "company",
            "rating",
            "skills",
            "pub_date",
            "url",
        ]
    )
    data = []

    def get_text(soup_tag):
        """
        Get soup object.
        Args:
            soup_tag: soup object containing information.
        Returns:
            str: text from soup object or None.
        """
        try:
            return soup_tag.text
        except:
            return None

    for id in vacancies_id:
        url = "https://hh.ru/vacancy/" + id
        headers = {"User-Agent": UserAgent().random}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print("Error", response.status_code)
            df = df.append(
                pd.DataFrame(
                    data,
                    columns=[
                        "id",
                        "vacancy_name",
                        "experience",
                        "work_type",
                        "busyness",
                        "city",
                        "company",
                        "rating",
                        "skills",
                        "pub_date",
                        "url",
                    ],
                )
            )
            return df

        try:
            soup = BeautifulSoup(response.text)
            name = get_text(
                soup.find("h1", attrs={"data-qa": re.compile(r"vacancy-title*")})
            )
            company = get_text(
                soup.find(
                    "span", attrs={"class": re.compile(r"bloko-header-section-2*")}
                )
            )
            rating = get_text(
                soup.find(
                    "div",
                    attrs={"data-qa": "employer-review-small-widget-total-rating"},
                )
            )
            city = get_text(
                soup.find(
                    attrs={
                        "data-qa": re.compile(
                            r"(vacancy-view-location)|(vacancy-view-raw-address)"
                        )
                    }
                )
            ).split(", ")[0]
            exp = get_text(soup.find("span", attrs={"data-qa": "vacancy-experience"}))
            work_type, busyness = get_text(
                soup.find("p", attrs={"data-qa": "vacancy-view-employment-mode"})
            ).split(", ")
            pub_date = get_text(
                soup.find(
                    "p", attrs={"class": "vacancy-creation-time-redesigned"}
                ).findChild("span")
            )
            skills = [
                get_text(skill)
                for skill in (soup.find_all("li", attrs={"data-qa": "skills-element"}))
            ]
            data.append(
                [
                    id,
                    name,
                    exp,
                    work_type,
                    busyness,
                    city,
                    company,
                    rating,
                    skills,
                    pub_date,
                    url,
                ]
            )
        except:
            continue

        if counter % 10 == 0:
            print(f"Vacancy № {counter}")
            df = df.append(
                pd.DataFrame(
                    data,
                    columns=[
                        "id",
                        "vacancy_name",
                        "experience",
                        "work_type",
                        "busyness",
                        "city",
                        "company",
                        "rating",
                        "skills",
                        "pub_date",
                        "url",
                    ],
                )
            )
            data = []
        counter += 1

    return df


def str_to_list(string):
    """
    Convert a string representation of a list into a list.
    Args:
        string (str): a string representation of a list. The string should be formatted 
                      as a Python list, with elements separated by commas and enclosed 
                      in square brackets.
    Returns:
        list: a list containing the elements from the input string.
    """
    if string:
        string = string.strip("[]")
        return [elem.strip("'") for elem in string.split(", ")]
    else:
        return None


def str_to_date(str):
    """
    Convert a string representation of a date into a date object.
    Args:
        str (str): a string representation of a date in the format "date monthname year".
    Returns:
        date: a date object representing the input string.
    """
    months = {
        "января": "1",
        "февраля": "2",
        "марта": "3",
        "апреля": "4",
        "мая": "5",
        "июня": "6",
        "июля": "7",
        "августа": "8",
        "сентября": "9",
        "октября": "10",
        "ноября": "11",
        "декабря": "12",
    }
    pattern = re.compile(r"([а-я]+)")
    month = re.findall(pattern, str)
    date = re.sub(pattern, months["".join(month)], str)

    return datetime.strptime(date, "%d %m %Y").date()


def categorize_vacancy(vacancy_name):
    """
    Categorize a vacancy based on its name.
    Args:
        vacancy_name (str): the name of the vacancy.
    Returns:
        str: the category of the vacancy.
    """
    if re.search(
        r"(.*data.+anal.*)|(.*data.+анал.*)|(.*анал.*дан.*)|(\bda\b)",
        vacancy_name,
        flags=re.IGNORECASE,
    ):
        return "Data Analyst"
    elif re.search(
        r"(.*bi.+anal.*)|(\bbi\b)|(.*bi.+анал.*)|(.*анал.*bi.*)",
        vacancy_name,
        flags=re.IGNORECASE,
    ):
        return "BI Analyst"
    elif re.search(
        r"(.*product.*)|(.*prod.+анал.*)|(.*анал.*прод.*)|(.*продукт.*)",
        vacancy_name,
        flags=re.IGNORECASE,
    ):
        return "Product Analyst"
    elif re.search(
        r"(.*веб.*)|(.*web.+анал.*)|(.*анал.*web.*)|(\bweb\b)",
        vacancy_name,
        flags=re.IGNORECASE,
    ):
        return "Web Analyst"
    elif re.search(
        r"(.*engin.*)|(.*инжен.*)|(\bde\b)", vacancy_name, flags=re.IGNORECASE
    ):
        return "Data Engineer"
    elif re.search(
        r"(.*data.+scien.*)|(.*scien.*)|(\bds\b)", vacancy_name, flags=re.IGNORECASE
    ):
        return "Data Scientist"
    else:
        return "Other"


def skills_rating(df, specialization="Data Analyst"):
    """
    Calculate the popularity of skills required for a specific specialization.
    Args:
        df (pd.DataFrame): DataFrame containing vacancy information.
        specialization (str): the specialization for which to calculate 
                              skill popularity. Default is "Data Analyst".
    Returns:
        list: a list of tuples, where each tuple contains a skill and its popularity 
              (as a percentage of total vacancies).
    """
    data = df[(df["category"] == specialization)]

    total_vacancies = 0
    all_skills = []

    for skill in data["skills"]:
        if skill:
            all_skills.extend(skill)
            total_vacancies += 1

    result = sorted(Counter(all_skills).items(), key=lambda x: x[1], reverse=True)

    return [(skill, round((number / total_vacancies), 3)) for skill, number in result]


def get_and_save_data(vacancies, experience, days_period=1):
    """
    This function fetches vacancies based on the provided vacancies, experience, and days_period.
    It then fetches detailed information about these vacancies and saves them into a CSV file.
    Args:
        vacancies (list): a list of vacancy names to search for.
        experience (list): a list of experience levels to search for.
        days_period (int): the number of days back to search for vacancies. Default is 1.
    Returns:
        None
    """
    for exp in experience:
        print(f"Getting vacancies with experience: {exp}")
        df_new_vacancies = get_all_vacancies(
            vacancies, exp=exp, page=0, search_period=days_period
        )
        print(f"Getting information about vacancies with experience: {exp}")
        df_new_info = get_vacancy_info(list(df_new_vacancies["id"]))

        current_date = date.today().strftime("%d-%m-%Y")
        with open(f"{exp}_{current_date}", "w") as f:
            f.write(df_new_info.to_csv())
            print(f"The file {exp}_{current_date} was created\n")

    return None


def download_data(date=date.today().strftime("%d-%m-%Y")):
    """
    Downloads data from CSV files created by the get_and_save_data function.
    Args:
        date (str): The date in the format "dd-mm-yyyy". Default is the current date.
    Returns:
        pd.DataFrame: A DataFrame containing the downloaded data.
    """
    files = [file for file in os.listdir() if re.search(date, file)]
    result = pd.DataFrame()

    for file in files:
        df = pd.read_csv(open(file))
        df = df.drop(columns=["Unnamed: 0"])
        df.loc[df["skills"] == "[]", "skills"] = None
        result = pd.concat([result, df])

    return result


def plot_vacancies(df):
    """
    This function plots a bar chart showing the distribution of vacancies in the labor market.
    Args:
        df (pd.DataFrame): a DataFrame containing vacancy information. 
                           The DataFrame should have a column named 'category'.
    Returns:
        None. The function only displays a plot.
    """
    data = sorted(Counter(df["category"]).items(), key=lambda x: x[1])
    x = [value[0] for value in data]
    y = [value[1] for value in data]

    plt.bar(x, y, color=["orange"], width=0.5)
    plt.style.use("dark_background")
    plt.xticks(rotation=60)
    plt.grid(
        linestyle=":",
    )
    plt.title("Distribution of vacancies in the labor market")
    plt.ylabel("Number of vacancies")
    plt.show()
    return None


def plot_exp(df):
    """
    This function plots a bar chart showing the distribution of vacancies 
    depending on experience.
    Args:
        df (pd.DataFrame): a DataFrame containing vacancy information. 
                           The DataFrame should have a column named 'experience'.
    Returns:
        None. The function only displays a plot.
    """
    data = Counter(df["experience"]).items()
    x = [value[0] for value in data]
    y = [value[1] for value in data]

    plt.bar(x, y, color=["orange"], width=0.5)
    plt.style.use("dark_background")
    plt.xticks(rotation=60)
    plt.grid(
        linestyle=":",
    )
    plt.title("Distribution of vacancies depending on experience")
    plt.ylabel("Number of vacancies")
    plt.show()

    return None


def plot_work_format(df):
    """
    This function plots a bar chart showing the distribution of vacancies 
    depending on the format of the work.
    Args:
        df (pd.DataFrame): a DataFrame containing vacancy information. 
                           The DataFrame should have a column named 'busyness'.
    Returns:
        None. The function only displays a plot.
    """
    data = sorted(Counter(df["busyness"]).items(), key=lambda x: x[1])
    x = [value[0] for value in data]
    y = [value[1] for value in data]

    plt.bar(x, y, color=["orange"], width=0.4)
    plt.style.use("dark_background")
    plt.xticks(rotation=0)
    plt.grid(
        linestyle=":",
    )
    plt.title("Distribution of vacancies depending on the format of the work")
    plt.ylabel("Number of vacancies")
    plt.show()

    return None


def plot_map(df):
    """
    This function plots a map of Russia with circles representing cities. 
    The size and color of the circles are determined by the number of vacancies in each city.
    Args:
        df (pd.DataFrame): a DataFrame containing vacancy information. 
                           The DataFrame should have a column named 'city'.
    Returns:
        map (folium.Map): a folium map object with the plotted circles.
    """
    data = sorted(Counter(df["city"]).items(), key=lambda x: x[1], reverse=True)

    map = folium.Map(location=[55.7522, 37.6156], zoom_start=4)
    geolocator = Nominatim(user_agent="myuseragent")

    def city_color(num_vacancies):
        if num_vacancies > 1000:
            return "red"
        elif 500 <= num_vacancies < 1000:
            return "orange"
        elif 100 <= num_vacancies < 500:
            return "yellow"
        elif 10 <= num_vacancies < 100:
            return "green"
        else:
            return "white"

    def city_radius(num_vacancies):
        if num_vacancies > 1000:
            return 20
        elif 500 <= num_vacancies < 1000:
            return 15
        elif 100 <= num_vacancies < 500:
            return 12
        elif 10 <= num_vacancies < 100:
            return 8
        else:
            return 4

    for city, num_vacancies in data:
        try:
            location = geolocator.geocode(city)
            folium.CircleMarker(
                location=[location.latitude, location.longitude],
                radius=city_radius(num_vacancies),
                tooltip=city,
                popup=f"{num_vacancies}",
                fill_color=city_color(num_vacancies),
                fill_opacity=0.9,
            ).add_to(map)
        except:
            continue

    return map


def plot_skills(df, specializations):
    """
    This function plots a horizontal bar chart showing the necessary skills 
    for a specific specialization. The skills are sorted by their popularity 
    in the given DataFrame.
    Args:
        df (pd.DataFrame): A DataFrame containing vacancy information. 
                           The DataFrame should have a column named 'skills' 
                           and a column named 'category'.
        specializations (list): A list of specialization names for which to plot 
                                the necessary skills.
    Returns:
        None. The function only displays a plot.
    """
    for spec in specializations:
        data = skills_rating(df=df, specialization=spec)
        data = [(skill, pop * 100) for skill, pop in data if pop >= 0.05]

        x = [value[0] for value in data]
        y = [value[1] for value in data]

        plt.figure(figsize=(15, 10))
        plt.barh(x, y, color=["orange"])
        plt.style.use("dark_background")
        plt.grid(
            linestyle=":",
        )
        plt.title(f"The necessary skills for {spec}")
        plt.xlabel("The percentage of demand for the skill")
        plt.ylabel("Skills")
        plt.show()
        
    return None
