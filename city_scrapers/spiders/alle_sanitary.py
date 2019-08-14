import datetime

from city_scrapers_core.constants import NOT_CLASSIFIED
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider

month_lookup = {
    'April': 4,
    'December': 12,
    'March': 3,
    'October': 10,
    'September': 9,
    'August': 8,
    'February': 2,
    'May': 5,
    'January': 1,
    'November': 11,
    'June': 6,
    'July': 7,
}


class AlleSanitarySpider(CityScrapersSpider):
    name = "alle_sanitary"
    agency = "Allegheny County Sanitary Authority (ALCOSAN)"
    timezone = "America/New_York"
    allowed_domains = ["www.alcosan.org"]
    site = "http://www.alcosan.org/BoardofDirectors"
    start_urls = [site + "/2015MeetingSchedule/tabid/195/Default.aspx"]

    # Xcode for dates div //div[@class="Normal"]/p

    def parse(self, response):
        """
        `parse` should always `yield` Meeting items.

        Change the `_parse_title`, `_parse_start`, etc methods to fit your scraping
        needs.
        """
        dates = response.xpath("//p").extract()[0].split('<br>\r\n')
        for item in dates:
            if 'day' in item:
                meeting = Meeting(
                    title=self._parse_title(item),
                    description=self._parse_description(item),
                    classification=self._parse_classification(item),
                    start=self._parse_start(item),
                    end=self._parse_end(item),
                    all_day=self._parse_all_day(item),
                    time_notes=self._parse_time_notes(item),
                    location=self._parse_location(item),
                    links=self._parse_links(item),
                    source=self._parse_source(response),
                )

                meeting["status"] = self._get_status(meeting)
                meeting["id"] = self._get_id(meeting)

                yield meeting

    def _parse_title(self, item):
        """Parse or generate meeting title."""
        return "ALCOSAN Board Meeting"

    def _parse_description(self, item):
        """Parse or generate meeting description."""
        return "board meeting"

    def _parse_classification(self, item):
        """Parse or generate classification from allowed options."""
        return NOT_CLASSIFIED

    def _parse_start(self, item):
        """Parse start datetime as a naive datetime object."""
        dow, date, year = item.split(",")
        month, day = date.split()
        year = year.split("\\")[0]
        month = month_lookup[month]
        return datetime.datetime(int(year), int(month), int(day), 16, 30)

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
        return {
            "address": "3300 Preble Avenue, Pittsburgh, PA 15233",
            "name": "William C. Trefz Boardroom",
        }

    def _parse_links(self, item):
        """Parse or generate links."""
        return [{"href": "", "title": ""}]

    def _parse_source(self, response):
        """Parse or generate source."""
        return response.url
