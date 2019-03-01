from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import BOARD
from freezegun import freeze_time
from scrapy.http import HtmlResponse, Request, TextResponse

from city_scrapers.spiders.pitt_zoning import PittZoningSpider


def file_response(file_name, url=None):
    """
    This function from core needed modifications to process binary pdfs
    the import an be re-enabled once the change is accepted in core
    # from city_scrapers_core.utils import file_response

    Create a Scrapy fake HTTP response from a HTML file
    @param file_name: The relative filename from the tests directory,
                      but absolute paths are also accepted.
    @param url: The URL of the response.
    returns: A scrapy HTTP response which can be used for unittesting.

    Based on https://stackoverflow.com/a/12741030, a nice bit of hacking.
    """
    if not url:
        url = "http://www.example.com"

    if file_name[-4:].lower() == ".pdf":
        request = Request(url=url)
        with open(file_name, "rb") as f:
            file_content = f.read()
            body = file_content
    else:
        request = Request(url=url)
        with open(file_name, "r", encoding="utf-8") as f:
            file_content = f.read()
        body = str.encode(file_content)

    if file_name[-5:] == ".json":
        body = file_content
        return TextResponse(url=url, body=body, encoding="utf-8")

    return HtmlResponse(url=url, request=request, body=body)


test_response = file_response(
    join(dirname(__file__), "files", "4496_ZBA_Agenda__01-10-19.pdf"),
    url="http://apps.pittsburghpa.gov/redtail/images/4496_ZBA_Agenda__01-10-19.pdf",
)

spider = PittZoningSpider()

freezer = freeze_time("2019-02-23")
freezer.start()

parsed_items = [item for item in spider.parse_PDF(test_response)]

freezer.stop()


def test_tests():
    print("Please write some tests for this spider.")
    assert True


"""
Uncomment below
"""


def test_title():
    assert "zoning" in parsed_items[0]["title"].lower()


def test_description():
    assert "\n" in parsed_items[0]["description"].lower()


def test_start():
    assert parsed_items[0]["start"] > datetime(1970, 1, 1, 0, 0)


# def test_end():
#     assert parsed_items[0]["end"] > datetime(1970, 1, 1, 0, 0)

# def test_time_notes():
#     assert parsed_items[0]["time_notes"] == "EXPECTED TIME NOTES"

# def test_id():
#     assert parsed_items[0]["id"] == "EXPECTED ID"

# def test_status():
#     assert parsed_items[0]["status"] == "EXPECTED STATUS"


def test_location():
    assert "" in parsed_items[0]["location"]["name"].lower()
    assert "" in parsed_items[0]["location"]["address"].lower()


def test_source():
    assert "http" in parsed_items[0]["source"].lower()


# def test_links():
#     assert parsed_items[0]["links"] == [{
#       "href": "EXPECTED HREF",
#       "title": "EXPECTED TITLE"
#     }]


def test_classification():
    assert parsed_items[0]["classification"] == BOARD


@pytest.mark.parametrize("item", parsed_items)
def test_all_day(item):
    assert item["all_day"] is False
