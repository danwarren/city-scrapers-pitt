"""
        Copyright (C) 2019 Daniel Warren For cityscrapers Pittsburgh
"""

import re
from datetime import datetime
from tempfile import TemporaryFile
from urllib.request import urlopen

from city_scrapers_core.constants import BOARD
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from PyPDF2 import PdfFileReader
from scrapy import Request

pageRE1 = re.compile(
    r'(?P<title>[\s\S]*)(?P<date>'
    r'(?P<month>J(anuary|u(ne|ly))|February|Ma(rch|y)|A(pril|ugust)|(((Sept|Nov|Dec)em)|Octo)ber)'
    r'\s+(?P<day>\d{1,2})\,\s+(?P<year>\d{4}))[\s\S]?(Date|Time)\sof\sHearing:'
)

pageRE2 = re.compile(
    r'(?P<hour>\d{1,2})\:(?P<minute>\d{2})(?P<description>[\s\S]*?)\n{8,50}'
    r'(?P<address>(?P<address1>.*?)(?P<address2>\d{1,9}[\s\S]*\d{5}))?'
)

monthLookup = {
    'january': 1,
    'february': 2,
    'march': 3,
    'april': 4,
    'may': 5,
    'june': 6,
    'july': 7,
    'august': 8,
    'september': 9,
    'october': 10,
    'november': 11,
    'december': 12,
}


def PDFtxtFromURL(url):
    """ Extract the text from all pages of a web hosted PDF
        Return a dict with cleaned up strings for each page
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
    return (output)


def PDFtxtFromResponse(response):
    """ Extract the text from all pages of a web hosted PDF
        Return a dict with cleaned up strings for each page
    """
    output = {}
    tempFilePDF = TemporaryFile()
    tempFilePDF.write(response.body)
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
        self.logger.debug('Parse function called on %s', response.url)
        for item in response.xpath('//tr[@class=\'data\']//a/@href'):
            thisItem = item.extract()
            self.logger.debug('xpath found %s', thisItem)
            request = Request(thisItem, callback=self.parse_PDF)
            yield request

    def parse_PDF(self, response):
        """
        `parse` should always `yield` Meeting items.
        """
        self.logger.debug('Parse_PDF function called on %s', response.url)
        Pages = PDFtxtFromResponse(response)
        firstPage = Pages[0]
        for PageNum, PageText in Pages.items():
            meeting = Meeting(
                title=self._parse_title(PageText),
                description=self._parse_description(PageText),
                classification=self._parse_classification(PageText),
                start=self._parse_start(PageText),
                end=self._parse_end(PageText),
                all_day=self._parse_all_day(PageText),
                time_notes=self._parse_time_notes(PageText),
                location=self._parse_location(firstPage),
                links=self._parse_links(response),
                source=self._parse_source(response),
            )
            meeting["status"] = self._get_status(meeting)
            meeting["id"] = self._get_id(meeting)
            yield meeting

    def _parse_title(self, item):
        """Parse or generate meeting title."""
        title = pageRE1.search(item).group('title')
        return title

    def _parse_description(self, item):
        """Parse or generate meeting description."""
        description = pageRE2.search(item).group('description')
        return description

    def _parse_classification(self, item):
        """Parse or generate classification from allowed options."""
        return BOARD

    def _parse_start(self, item):
        """Parse start datetime as a naive datetime object."""
        S1 = pageRE1.search(item).groupdict()
        S2 = pageRE2.search(item).groupdict()
        hour = int(S2['hour'])
        minute = int(S2['minute'])
        year = int(S1['year'])
        monthWord = S1['month']
        month = monthLookup[monthWord.lower()]
        day = int(S1['day'])
        start = datetime(year, month, day, hour, minute)
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
        S2 = pageRE2.search(item).groupdict()
        address = S2['address2']
        name = S2['address1']
        return {
            "address": address,
            "name": name,
        }

    def _parse_links(self, item):
        """Parse or generate links."""
        return [{"href": item, "title": item}]

    def _parse_source(self, response):
        """Parse or generate source."""
        return response.url


# vim: set ts=4 sw=4 expandtab
