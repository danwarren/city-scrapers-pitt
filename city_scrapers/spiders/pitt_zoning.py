from city_scrapers_core.constants import NOT_CLASSIFIED, BOARD
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from PyPDF2 import PdfFileReader
from urllib.request import urlopen
from tempfile import TemporaryFile
import re


pageRE1 = re.compile('(?P<title>[\s\S]*)(?P<date>(?P<month>J(anuary|u(ne|ly))|February|Ma(rch|y)|A(pril|ugust)|(((Sept|Nov|Dec)em)|Octo)ber)\s+(?P<day>\d{1,2})\,\s+(?P<year>\d{4}))')

pageRE2 = re.compile('(?P<start>\d{1}\:\d{2})(?P<description>[\s\S]*?)\n{4,50}(?P<address>.*\d{1,9}[\s\S]*\d{5})?')

# from enchant import Dict
# d = Dict("en_US")


def PDFtxtFromURL(url):
    """ Extract the text from all pages of a web hosted PDF
        Return a dict with cleaned up strings for each page

        Copyright (C) 2019 Daniel Warren For cityscrapers Pittsburgh
    """
    output = {}
    tempFilePDF = TemporaryFile()
    urlHandle = urlopen(url)
    while True:
        data = urlHandle.read(16384)
        if not data:
            break
        tempFilePDF.write(data)
    PFR = PdfFileReader(tempFilePDF)
    for PDFPageNum in range(PFR.getNumPages()):
        PDFPage = PFR.getPage(PDFPageNum)
        rawPage = PDFPage.extractText().split('\n')
        Page = ""
        for i in rawPage:
            line = i.strip()
            final = ""
            if line:
                for j in line.split():
                    word = j.strip()
                    if word:
                        final += word + " "
            Page += final.strip() + '\n'
        output[PDFPageNum] = Page
    return(output)


class PittZoningSpider(CityScrapersSpider):
    name = "pitt_zoning"
    agency = "Pittsburgh Zoning Board of Adjustment"
    timezone = "America/New_York"
    allowed_domains = ["pittsburghpa.gov"]
    start_urls = ["http://pittsburghpa.gov/dcp/zba-schedule"]

    def parse(self, response):
        """
        `parse` should always `yield` Meeting items.

        Change the `_parse_id`, `_parse_name`, etc methods to fit your scraping
        needs.
        """
        for item in response.xpath('//tr[@class="data"]//a/@href'):
            Pages = PDFtxtFromURL(item)
            firstPage = Pages[0]
            for PageNum, PageText in Pages:
                meeting = Meeting(
                    title=self._parse_title(PageText),
                    description=self._parse_description(PageText),
                    classification=self._parse_classification(PageText),
                    start=self._parse_start(PageText),
                    end=self._parse_end(PageText),
                    all_day=self._parse_all_day(PageText),
                    time_notes=self._parse_time_notes(item),
                    location=self._parse_location(firstPage),
                    links=self._parse_links(item),
                    source=self._parse_source(response),
                )

                meeting["status"] = self._get_status(meeting)
                meeting["id"] = self._get_id(meeting)

                yield meeting

    def _parse_title(self, item):
        """Parse or generate meeting title."""
        title = pageRE(item).group('title')
        return title

    def _parse_description(self, item):
        """Parse or generate meeting description."""
        description = pageRE(item).group('description')
        return description

    def _parse_classification(self, item):
        """Parse or generate classification from allowed options."""
        return BOARD

    def _parse_start(self, item):
        """Parse start datetime as a naive datetime object."""
        start = pageRE(item).group('start')
        return start

    def _parse_end(self, item):
        """Parse end datetime as a naive datetime object. Added by pipeline if None"""
        return None

    def _parse_time_notes(self, item):
        """Parse any additional notes on the timing of the meeting"""
        return ""

    def _parse_all_day(self, item):
        """Parse or generate all-day status. Defaults to False."""
        return False

    def _parse_location(self, item):
        """Parse or generate location."""
        address = pageRE(item).group('address')
        return {
            "address": address,
            "name": "",
        }

    def _parse_links(self, item):
        """Parse or generate links."""
        return [{"href": item, "title": item}]

    def _parse_source(self, response):
        """Parse or generate source."""
        return response.url


# vim: set ts=4 sw=4 expandtab
