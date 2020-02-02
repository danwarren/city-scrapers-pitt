"""
        Copyright (C) 2019 Daniel Warren For cityscrapers Pittsburgh
"""

import os
import re
from datetime import datetime
from tempfile import TemporaryFile

from city_scrapers_core.constants import BOARD
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from PyPDF2 import PdfFileReader
from scrapy import Request

DEBUG = False
"""
if DEBUG is True, break all parse loops after first run
"""
if os.getenv('TRAVIS_DEBUG_STATE') == 'DEBUG':
    DEBUG = True

pageRE1 = re.compile(
    r'(?P<before>[\s\S]*?)?'
    r'(?P<title>[\s\S]*)(?P<date>'
    r'(?P<month>J(anuary|u(ne|ly))|February|Ma(rch|y)|A(pril|ugust)|(((Sept|Nov|Dec)em)|Octo)ber)'
    r'\s+(?P<day>\d{1,2})\,\s+(?P<year>\d{4}))[\s\S]?(Date|Time)\sof\sHearing:'
    r'(?P<after>[\s\S]*)?'
)

dateRE = re.compile(
    r'(?P<before>[\s\S]*?)?'
    r'(?P<date>'
    r'(?P<month>J(anuary|u(ne|ly))|February|Ma(rch|y)|'
    r'A(pril|ugust)|(((Sept|Nov|Dec)em)|Octo)ber)'
    r'\s+(?P<day>\d{1,2})\,\s+(?P<year>\d{4}))'
    r'(?P<after>[\s\S]*)?'
)

date2RE = re.compile(
    r'(?P<before>[\s\S]*?)?'
    r'(?P<date>'
    r'(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|'
    r'Aug|Sep|Oct|Nov|Dec)\s+'
    r'(?P<day>\d{1,2})\,?\s+(?P<year>\d{4}))'
    r'(?P<after>[\s\S]*)?'
)

pageRE2 = re.compile(
    r'(?P<before>[\s\S]*?)?'
    r'(?P<hour>\d{1,2})\:(?P<minute>\d{2})(?P<description>[\s\S]*?)\n{8,50}'
    r'(?P<address>(?P<address1>.*?)(?P<address2>\d{1,9}[\s\S]*\d{5}))?'
    r'(?P<after>[\s\S]*)?'
)

descriptionRE = re.compile(
    r'(?P<before>[\s\S]*?)?'
    r'\:(?P<description>[\s\S]*?)\n{8,50}'
    r'(?P<after>[\s\S]*)?'
)

timeRE = re.compile(
    r'(?P<before>[\s\S]*?)?'
    r'(?P<time>(?P<hour>\d{1,2})\:(?P<minute>\d{2}))'
    r'(?P<after>[\s\S]*)?'
)

addressRE = re.compile(
    r'(?P<before>[\s\S]*?)?'
    r'(?P<address>\d{3,9}[\s\S]*?\d{5})?'
    r'(?P<after>[\s\S]*)?'
)

fourWordsRE = re.compile(r'(?P<words>\w{4})')

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


def PDFtxtFromResponse(response):
    """ Extract the text from all pages of a web hosted PDF
        Return a dict with cleaned up strings for each page
    """
    output = {'title': '', 'pages': {}}
    tempFilePDF = TemporaryFile()
    tempFilePDF.write(response.body)
    PFR = PdfFileReader(tempFilePDF)
    try:
        title = PFR.getDocumentInfo()['title']
        output['title'] = title
    except KeyError:
        pass
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
        output['pages'][PDFPageNum] = Page
    return (output)


class PittZoningSpider(CityScrapersSpider):
    name = "pitt_zoning"
    agency = "Pittsburgh Zoning Board of Adjustment"
    timezone = "America/New_York"
    allowed_domains = ["pittsburghpa.gov", "apps.pittsburghpa.gov"]
    start_urls = ["http://pittsburghpa.gov/dcp/zba-schedule"]

    def parse(self, response):
        """
        `parse` should always `yield` Meeting items.
        in this case we find agenda PDFs and cllback to
        parse_PDF which yeilds meetings.
        """
        self.logger.debug('Parse function called on %s', response.url)
        title = response.xpath('//title')[0]
        for item in response.xpath('//tr[@class=\'data\']'):
            href = item.xpath('.//a/@href')[0]
            date = item.xpath('.//td[2]')
            thisDate = date.extract()
            try:
                month, day, year = thisDate.split('/')
            except AttributeError:
                month, day, year = (1, 1, 1)
            thisItem = href.extract()
            self.logger.debug('xpath found %s', thisItem)
            request = Request(thisItem, callback=self.parse_PDF)
            if title:
                request.meta['title'] = title
            if month and day and year:
                request.meta['date'] = datetime(year, month, day, 0, 0)
            yield request
            if DEBUG:
                break

    def parse_PDF(self, response):
        """
        `parse` should always `yield` Meeting items.
        """
        self.logger.debug('Parse_PDF function called on %s', response.url)
        resp = PDFtxtFromResponse(response)
        Pages = resp['pages']
        # title = resp['title']
        default_title = response.meta['title']
        if not default_title:
            default_title = "Unknown Title"
        default_date = response.meta['date']
        if not default_date:
            default_date = datetime(1, 1, 1, 0, 0)
        firstPage = Pages[0]
        for PageNum, PageText in Pages.items():
            REout = fourWordsRE.search(PageText)
            if REout:
                words = REout.group('words')
            else:
                words = None
            if words:
                meeting = Meeting(
                    title=self._parse_title(PageText, default_title),
                    description=self._parse_description(PageText),
                    classification=self._parse_classification(PageText),
                    start=self._parse_start(PageText, default_date),
                    end=self._parse_end(PageText),
                    all_day=self._parse_all_day(PageText),
                    time_notes=self._parse_time_notes(PageText),
                    location=self._parse_location(firstPage),
                    links=self._parse_links(response),
                    source=self._parse_source(response),
                )
                meeting["links"][0]['page'] = PageNum
                meeting["status"] = self._get_status(meeting)
                meeting["id"] = self._get_id(meeting)
                yield meeting
            if DEBUG:
                break

    def _parse_title(self, item, default_title='ZONING BOARD OF ADJUSTMENT HEARING AGENDA'):
        """Parse or generate meeting title."""
        title = None
        REout = pageRE1.search(item)
        if REout:
            title = REout.group('title')
            REout = fourWordsRE.search(title)
        if not REout:
            title = default_title
        return title

    def _parse_description(self, item):
        """Parse or generate meeting description."""
        description = None
        REout = pageRE2.search(item)
        if REout:
            description = REout.group('description')
        else:
            REout = descriptionRE.search(item)
            if REout:
                description = REout.group('description')
        if not description:
            description = 'NO MATCH -- FULL TEXT: ' + item
        else:
            tmp = ""
            for line in description:
                if line != '\n':
                    tmp += line
            description = tmp
        return description

    def _parse_classification(self, item):
        """Parse or generate classification from allowed options."""
        return BOARD

    def _parse_start(self, item, default_date=datetime(1, 1, 1, 0, 0)):
        """Parse start datetime as a naive datetime object."""
        REout = pageRE2.search(item)
        if REout:
            S2 = REout.groupdict()
            hour = int(S2['hour'])
            minute = int(S2['minute'])
        else:
            REout = timeRE.search(item)
            if REout:
                T1 = REout.groupdict()
                hour = int(T1['hour'])
                minute = int(T1['minute'])
            else:
                hour = default_date.hour
                minute = default_date.minute
        REout = pageRE1.search(item)
        if REout:
            S1 = REout.groupdict()
            year = int(S1['year'])
            monthWord = S1['month']
            month = monthLookup[monthWord.lower()]
            day = int(S1['day'])
        else:
            REout = dateRE.search(item)
            if REout:
                S1 = REout.groupdict()
                year = int(S1['year'])
                monthWord = S1['month']
                month = monthLookup[monthWord.lower()]
                day = int(S1['day'])
            else:
                year = default_date.year
                month = default_date.month
                day = default_date.day
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
        address = None
        name = None
        REout = pageRE2.search(item)
        if REout:
            S2 = REout.groupdict()
            address = S2['address2']
            name = S2['address1']
        else:
            REout = addressRE.search(item)
            if REout:
                S2 = REout.groupdict()
                address = S2['address2']
                name = S2['address1']
        if not address:
            address = '200 Ross Street, Third Floor\nPittsburgh, Pennsylvania 15219 DEFAULT'
        if not name:
            name = 'City of Pittsburgh, Department of City Planning'
        return {
            "address": address,
            "name": name,
            "coordinates": None,
        }

    def _parse_links(self, item):
        """Parse or generate links."""
        return [{"href": item.url, "title": "Agenda PDF"}]

    def _parse_source(self, response):
        """Parse or generate source."""
        return response.url


# vim: set ts=4 sw=4 expandtab