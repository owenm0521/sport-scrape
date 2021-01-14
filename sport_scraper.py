#WEB SCRAPER

from selenium import webdriver
import pandas
import selenium.common.exceptions
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import data
from urllib.parse import urlparse
from lxml import etree


class SportScraper:
    def __init__(self, sport_name, url, path):
        self.sport = data.Sport(sport_name)
        self.url = url
        self.path = path
        self.driver = self.__create_driver()
        self.pages = self.__get_market_pages()
        self.__get_players() if sport_name == 'NBA' else self.__get_events()
        self.lines_and_sportsbooks = self.__get_lines_and_books()
        self.data = data.Table()
        for i in range(len(self.pages)):
            self.__scrape_NBA_table(self.pages[i], i) if sport_name == 'NBA' else self.__scrape_PGA_table(self.pages[i], i)

    def __create_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
        driver = webdriver.Chrome(executable_path=self.path, options=options)
        return driver

    def __open_sport_page(self):
        driver = self.driver
        driver.get(self.url)
        xpath = "//button[@class='btn btn-light' and text()='%s']" % self.sport.sport_name
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
        button = driver.find_elements_by_xpath(xpath)[1]
        ActionChains(driver).move_to_element(button).click(button).perform()

    def __get_markets(self):
        self.__open_sport_page()
        markets = self.driver.find_elements_by_class_name('btn-group')[1]
        market_xpath = ".//button[@type='button']"
        markets = markets.find_elements_by_xpath(market_xpath)
        markets = [market.text for market in markets]
        return markets

    def __get_market_pages(self):
        markets = self.__get_markets()
        market_pages = []
        for market in markets:
            # add market to sport
            curr_market = data.Market(market)
            self.sport.markets.append(curr_market)
            # refresh page
            self.driver.refresh()
            # wait for page load
            WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, 'html')))
            WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.TAG_NAME, 'html')))
            while True:
                x = self.driver.execute_script("return document.readyState")
                if x == "complete":
                    break
            # switch to current market page
            market_xpath = "//span[text()='%s']" % str(market)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, market_xpath)))
            button = self.driver.find_elements_by_xpath(market_xpath)[0]
            ActionChains(self.driver).move_to_element(to_element=button).click(on_element=button).perform()
            # wait for page load
            WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, 'html')))
            WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.TAG_NAME, 'html')))
            while True:
                x = self.driver.execute_script("return document.readyState")
                if x == "complete":
                    break
            # save page
            html = self.driver.execute_script('return document.body.outerHTML;')
            tree = etree.HTML(html)
            # get unavailable rows
            table_xpaths = ["//div[@class='ag-pinned-left-cols-container']",
                            "//div[@class='ag-center-cols-clipper']//div[@class='ag-center-cols-viewport']//div[@class='ag-center-cols-container']" ]
            table_classes = ['ag-pinned-left-cols-container', 'ag-center-cols-container']
            for t in range(len(table_xpaths)):
                # get table
                while True:
                    try:
                        # scroll to top
                        html = self.driver.find_element_by_tag_name('html')
                        html.click()
                        html.send_keys(Keys.PAGE_UP)
                        ActionChains(self.driver).move_to_element(to_element=html).click(on_element=html).perform()
                        ActionChains(self.driver).send_keys(Keys.PAGE_UP).perform()
                        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys(Keys.HOME).perform()
                        # wait for table load
                        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, 'html')))
                        WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.TAG_NAME, 'html')))
                        stale_element = True
                        while stale_element:
                            try:
                                self.driver.find_element_by_class_name(table_classes[t])
                                stale_element = False
                            except selenium.common.exceptions.StaleElementReferenceException:
                                stale_element = True
                        table = self.driver.find_element_by_class_name(table_classes[t])
                        ActionChains(self.driver).move_to_element(to_element=table).perform()
                        break
                    except (Exception, selenium.common.exceptions):
                        continue
                # scroll down until bottom of page
                self.driver.implicitly_wait(1)
                last_row_index = 30
                while True:
                    try:
                        # wait for table load
                        stale_element = True
                        while stale_element:
                            try:
                                self.driver.find_element_by_class_name(table_classes[t])
                                stale_element = False
                            except selenium.common.exceptions.StaleElementReferenceException:
                                stale_element = True
                        # wait for table rows load
                        row_xpath = "//div[@row-index='%d']" % last_row_index
                        stale_element = True
                        while stale_element:
                            try:
                                scroll_to = self.driver.find_element_by_xpath(table_xpaths[t] + row_xpath)
                                stale_element = False
                            except selenium.common.exceptions.StaleElementReferenceException:
                                stale_element = True
                        # scroll to new rows
                        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, table_xpaths[t] + row_xpath)))
                        ActionChains(self.driver).move_to_element(to_element=scroll_to).click(on_element=scroll_to).perform()
                        WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH, table_xpaths[t] + row_xpath)))
                        self.driver.implicitly_wait(1)
                        # save new table
                        temp_table_html = etree.HTML(self.driver.execute_script("return document.body.outerHTML;"))
                        rows = temp_table_html.xpath(table_xpaths[t])[0].xpath(".//div[@role='row']")
                        # save new rows from table
                        for row in rows:
                            if int(row.get('row-index')) > last_row_index:
                                tree.xpath(table_xpaths[t])[0].append(row)
                        last_row_index += 13
                    except selenium.common.exceptions.StaleElementReferenceException:
                        continue
                    except selenium.common.exceptions.NoSuchElementException:
                        break
            market_pages.append(tree)
        self.driver.quit()
        return market_pages

    def __get_players(self):
        # for each market/event, get players/teams
        for market_page in range(len(self.pages)):
            player_xpath = ".//span[@class='pl-1']"
            players = self.pages[market_page].xpath(player_xpath)
            for i in range(len(players)):
                players[i] = players[i].text
            self.__get_games_by_players(market_page, players)

    def __get_games_by_players(self, market_index, players):
        i = 0
        while i < (len(players) - 1):
            curr_event = data.Event(players[i] + ' vs. ' + players[i + 1])
            curr_event.players.append(data.Player(players[i]))
            curr_event.players.append(data.Player(players[i + 1]))
            self.sport.markets[market_index].events.append(curr_event)
            i += 2

    def __get_events(self):
        for market_page in range(len(self.pages)):
            event_container_xpath = "//div[@class='ag-full-width-container']"
            event_container = self.pages[market_page].xpath(event_container_xpath)
            for e in event_container:
                all_events = e.xpath(".//span[@class='ag-group-value']")
                if len(all_events) > 0:
                    break
            event_xpath = ".//i[@class='fa fa-golf-ball pr-1']"
            event_text_xpath = ".//span[not(@*)]/text()"
            for i in range(len(all_events)):
                event = all_events[i].xpath(event_xpath)
                if len(event) > 0:
                    event_text = all_events[i].xpath(event_text_xpath)[0]
                    self.sport.markets[market_page].events.append(data.Event(event_text))
            self.__get_players_by_event(market_page)

    def __get_players_by_event(self, market_index):
        curr_page = self.pages[market_index]
        curr_market = self.sport.markets[market_index]
        events = curr_market.events
        table_xpath = ".//div[@class='ag-pinned-left-cols-container']"
        table = curr_page.xpath(table_xpath)[0]
        table_rows_xpath = ".//div[@role='row']"
        table_rows = table.xpath(table_rows_xpath)

        max_row_index = 0
        for row in table_rows:
            try:
                if int(row.get('row-index')) > max_row_index:
                    max_row_index = int(row.get('row-index'))
            except TypeError:
                continue
        row_index = 1
        event_index = -1
        while row_index < (max_row_index + len(events) + 1):
            try:
                curr_row = table.xpath(".//div[@row-index='%d']" % row_index)[0]
                player = curr_row.xpath(".//span[@class='pl-1']")[0].text
                events[event_index].players.append(data.Player(player))
            except Exception:
                event_index += 1
            row_index += 1

    def __get_lines_and_books(self):
        for market_page in range(len(self.pages)):
            header_xpath = "//div[@class='ag-header ag-focus-managed ag-pivot-off']"
            headers = self.pages[market_page].xpath(header_xpath)[0]
            line_xpath = ".//span[contains(@class,'mb-0') and not(text()='Picks')]"
            lines = headers.xpath(line_xpath)
            for i in range(len(lines)):
                lines[i] = lines[i].text
            sportsbook_xpath = ".//img[@width='90px']"
            sportsbooks = headers.xpath(sportsbook_xpath)
            for i in range(len(sportsbooks)):
                sportsbooks[i] = parse_image_url(sportsbooks[i])
                lines.append(sportsbooks[i])
            lines_and_sportsbooks = lines
        return lines_and_sportsbooks

    def __scrape_NBA_table(self, market_table, market_index):
        table = market_table.xpath("//div[@class='ag-center-cols-container']")[0]
        curr_market = self.sport.markets[market_index]

        # rows (n)
        row_index = 0
        for i in range(len(curr_market.events) + 1):
            # row-index starts at 1
            i += 1

            # path to table row
            try:
                row_i_xpath = ".//div[@row-index='%d']" % i
                row_i = table.xpath(row_i_xpath)[0]
                curr_event = curr_market.events[row_index]
                row_index += 1
            except Exception:
                continue

            # players per cell (2)
            for k in range(len(curr_event.players)):

                # cols (10)
                col_index = 0
                for j in range(len(self.lines_and_sportsbooks) + 1):
                    # col-index starts at 3
                    j += 3

                    # col 3 = best line (+images)
                    best_line = False
                    if j == 3:
                        best_line = True

                    # col 4 = true line (+ %ev)
                    true_line = False
                    if j == 4:
                        true_line = True

                    # col 5 = picks (blocked)
                    if j == 5:
                        continue

                    # path to table row, column (cell)
                    row_i_col_j_xpath = ".//div[@aria-colindex='%d']" % j
                    row_i_col_j = row_i.xpath(row_i_col_j_xpath)[0]

                    if curr_market.market_name == 'Advanced':
                        # path to card
                        advanced_card_xpath = ".//div[@class='cell-renderer--odds']"
                        advanced_card = row_i_col_j.xpath(advanced_card_xpath)[0]

                        # no lines check
                        row_i_col_j_odds_xpath = ".//div[contains(@class,'d-flex flex-row-reverse')]"
                        no_lines_xpath = ".//div[@class='card']"
                        no_lines = True
                        try:
                            advanced_card.xpath(no_lines_xpath)[0]
                            row_i_col_j_odds = "No Lines"
                        except Exception:
                            row_i_col_j_odds = advanced_card.xpath(row_i_col_j_odds_xpath)
                            no_lines = False
                    else:
                        # path to card
                        # no lines check
                        no_lines = False
                        try:
                            try:
                                row_i_col_j_card_xpath = ".//div[@class='card ']"
                                row_i_col_j_card = row_i_col_j.xpath(row_i_col_j_card_xpath)[0]
                            except Exception:
                                row_i_col_j_card_xpath = ".//div[@class='card border-danger']"
                                row_i_col_j_card = row_i_col_j.xpath(row_i_col_j_card_xpath)[0]
                            row_i_col_j_odds_xpath = ".//div[@data-action-type='deeplink']"
                            row_i_col_j_odds = row_i_col_j_card.xpath(row_i_col_j_odds_xpath)
                        except Exception:
                            no_lines = True
                            row_i_col_j_odds = "No Lines"

                    if curr_market.market_name == 'Advanced':
                        # get odds for Advanced
                        if no_lines:
                            odds = data.OddsBySite(self.lines_and_sportsbooks[col_index], row_i_col_j_odds)
                            curr_event.players[k].odds.append(odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, odds.site_name, odds.odds))
                            continue
                        else:
                            all_odds = row_i_col_j_odds[k]
                            odds1_xpath1 = ".//div[@class='d-flex justify-content-between align-items-center']"
                            odds1_xpath2 = ".//span[@class=' undefined']"
                            odds2_xpath = ".//small[@style='padding-left:2px']"
                            try:
                                try:
                                    odds1 = all_odds.xpath(odds1_xpath1)[0]
                                except Exception:
                                    odds1 = all_odds.xpath(odds1_xpath2)[0]
                                odds2 = odds1.xpath(odds2_xpath)[0].text
                                odds1 = odds1.text
                            except Exception:
                                odds1 = '-'
                                odds2 = '-'
                            odds = (odds1, odds2)
                        if best_line:
                            # get best line sportsbook from image
                            try:
                                image_xpath = ".//img[@height='18px' and @width='18px']"
                                url = all_odds.xpath(image_xpath)[0]
                                sportsbook = self.lines_and_sportsbooks[col_index] + ': ' + parse_image_url(url)
                                best_line_odds = data.OddsBySite(sportsbook, odds)
                            except Exception:
                                best_line_odds = data.OddsBySite(self.lines_and_sportsbooks[col_index], odds)
                            curr_event.players[k].odds.append(best_line_odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, best_line_odds.site_name, best_line_odds.odds))
                        else:
                            # sportsbook
                            curr_event.players[k].odds.append(data.OddsBySite(self.lines_and_sportsbooks[col_index], odds))
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, self.lines_and_sportsbooks[col_index], odds))

                    elif curr_market.market_name == 'Spread':
                        # get odds for Spread
                        if no_lines:
                            odds = data.OddsBySite(self.lines_and_sportsbooks[col_index], row_i_col_j_odds)
                            curr_event.players[k].odds.append(odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, odds.site_name,
                                              odds.odds))
                            continue
                        else:
                            all_odds = row_i_col_j_odds[k]
                            odds1_xpath = ".//div[@class='d-flex justify-content-between align-items-center']"
                            odds1 = all_odds.xpath(odds1_xpath)[0].text
                            odds2_xpath = ".//small[@style='padding-left:2px']"
                            odds2 = all_odds.xpath(odds2_xpath)[0].text
                            odds = (odds1, odds2)

                        if best_line:
                            # get best line sportsbook from image
                            try:
                                image_xpath = ".//img[@height='18px' and @width='18px']"
                                url = row_i_col_j_card.xpath(image_xpath)[k]
                                sportsbook = self.lines_and_sportsbooks[col_index] + ': ' + parse_image_url(url)
                                best_line_odds = data.OddsBySite(sportsbook, odds)
                            except Exception:
                                best_line_odds = data.OddsBySite(self.lines_and_sportsbooks[col_index], odds)
                            curr_event.players[k].odds.append(best_line_odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, best_line_odds.site_name,
                                              best_line_odds.odds))
                        elif true_line:
                            # get %ev
                            try:
                                ev_xpath = ".//div[@style='margin-top:1px;margin-bottom:1px']"
                                ev = row_i_col_j_card.xpath(ev_xpath)[k].text
                                sportsbook = self.lines_and_sportsbooks[col_index] + ': ' + str(ev)
                            except Exception:
                                sportsbook = self.lines_and_sportsbooks[col_index]
                            true_line_odds = data.OddsBySite(sportsbook, odds)
                            curr_event.players[k].odds.append(true_line_odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, true_line_odds.site_name,
                                              true_line_odds.odds))
                        else:
                            # sportsbook
                            curr_event.players[k].odds.append(data.OddsBySite(self.lines_and_sportsbooks[col_index], odds))
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, self.lines_and_sportsbooks[col_index], odds))

                    elif curr_market.market_name == 'Moneyline':
                        # get odds for Moneyline
                        if no_lines:
                            odds = data.OddsBySite(self.lines_and_sportsbooks[col_index], row_i_col_j_odds)
                            curr_event.players[k].odds.append(odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, odds.site_name, odds.odds))
                            continue
                        else:
                            odds_xpath = ".//div[@class='d-flex justify-content-between align-items-center']"
                            odds = row_i_col_j_odds[k].xpath(odds_xpath)[0].text

                        if best_line:
                            # get best line sportsbook from image
                            try:
                                image_xpath = ".//img[@height='18px' and @width='18px']"
                                url = row_i_col_j_card.xpath(image_xpath)[k]
                                sportsbook = self.lines_and_sportsbooks[col_index] + ': ' + parse_image_url(url)
                                best_line_odds = data.OddsBySite(sportsbook, odds)
                            except Exception:
                                best_line_odds = data.OddsBySite(self.lines_and_sportsbooks[col_index], odds)
                            curr_event.players[k].odds.append(best_line_odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, best_line_odds.site_name,
                                              best_line_odds.odds))
                        elif true_line:
                            # get %ev
                            try:
                                ev_xpath = ".//div[@style='margin-top:1px;margin-bottom:1px']"
                                ev = row_i_col_j_card.xpath(ev_xpath)[k].text
                                sportsbook = self.lines_and_sportsbooks[col_index] + ': ' + str(ev)
                            except Exception:
                                sportsbook = self.lines_and_sportsbooks[col_index]
                            true_line_odds = data.OddsBySite(sportsbook, odds)
                            curr_event.players[k].odds.append(true_line_odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, true_line_odds.site_name,
                                              true_line_odds.odds))
                        else:
                            # sportsbook
                            curr_event.players[k].odds.append(data.OddsBySite(self.lines_and_sportsbooks[col_index], odds))
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, self.lines_and_sportsbooks[col_index], odds))

                    else:
                        # get odds for Over/Under
                        if no_lines:
                            odds = data.OddsBySite(self.lines_and_sportsbooks[col_index], row_i_col_j_odds)
                            curr_event.players[k].odds.append(odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, odds.site_name, odds.odds))
                            continue
                        else:
                            all_odds = row_i_col_j_odds[k]
                            odds1_xpath = ".//div[@class='d-flex justify-content-between align-items-center']"
                            odds1 = all_odds.xpath(odds1_xpath)[0].text
                            odds2_xpath = ".//small[@style='padding-left:2px']"
                            odds2 = all_odds.xpath(odds2_xpath)[0].text
                            odds = (odds1, odds2)

                        if best_line:
                            # get best line sportsbook from image
                            try:
                                image_xpath = ".//img[@height='18px' and @width='18px']"
                                url = row_i_col_j_card.fxpath(image_xpath)[k]
                                sportsbook = self.lines_and_sportsbooks[col_index] + ': ' + parse_image_url(url)
                                best_line_odds = data.OddsBySite(sportsbook, odds)
                            except Exception:
                                best_line_odds = data.OddsBySite(self.lines_and_sportsbooks[col_index], odds)
                            curr_event.players[k].odds.append(best_line_odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, best_line_odds.site_name,
                                              best_line_odds.odds))
                        elif true_line:
                            # get %ev
                            try:
                                ev_xpath = ".//div[@style='margin-top:1px;margin-bottom:1px']"
                                ev = row_i_col_j_card.xpath(ev_xpath)[k].text
                                sportsbook = self.lines_and_sportsbooks[col_index] + ': ' + str(ev)
                            except Exception:
                                sportsbook = self.lines_and_sportsbooks[col_index]
                            true_line_odds = data.OddsBySite(sportsbook, odds)
                            curr_event.players[k].odds.append(true_line_odds)
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, true_line_odds.site_name,
                                              true_line_odds.odds))
                        else:
                            # sportsbook
                            curr_event.players[k].odds.append(data.OddsBySite(self.lines_and_sportsbooks[col_index], odds))
                            self.data.rows.append(
                                data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                              curr_event.players[k].player_name, self.lines_and_sportsbooks[col_index], odds))

                    col_index += 1

    def __scrape_PGA_table(self, market_table, market_index):
        table = market_table
        curr_market = self.sport.markets[market_index]
        event_containers = self.pages[market_index].xpath(".//div[@class='ag-full-width-container']")
        for e in event_containers:
            all_events = e.xpath(".//span[@class='ag-group-value']")
            if len(all_events) > 0:
                event_container = e
                break
        all_events = event_container.xpath(".//div[@role='row']")

        # for each event
        for i in range(len(curr_market.events)):
            # find current event row
            curr_event = curr_market.events[i]
            event_text_xpath = ".//span[not(@*)]/text()"
            for event in all_events:
                text = event.xpath(event_text_xpath)[0]
                if text == curr_event.event_name:
                    event_row = int(event.attrib['row-index'])

            # rows
            player_index = 0
            row_index = event_row + 1
            while row_index < (len(curr_event.players) + event_row + 1):

                row_i_xpath = ".//div[@class='ag-center-cols-clipper']//div[@row-index='%d']" % row_index
                row_i = table.xpath(row_i_xpath)[0]

                # cols (10)
                line_index = 0
                for col_index in range(len(self.lines_and_sportsbooks) + 1):
                    # col-index starts at 3
                    col_index += 3

                    # col 3 = best line (+images)
                    best_line = False
                    if col_index == 3:
                        best_line = True

                    # col 4 = true line (+ %ev)
                    true_line = False
                    if col_index == 4:
                        true_line = True

                    # col 5 = picks (blocked)
                    if col_index == 5:
                        continue

                    # path to table row, column (cell)
                    row_i_col_j_xpath = ".//div[@aria-colindex='%d']" % col_index
                    row_i_col_j = row_i.xpath(row_i_col_j_xpath)[0]

                    # path to cell card
                    row_i_col_j_card_xpath = ".//div[contains(@class,'card')]"
                    row_i_col_j_card = row_i_col_j.xpath(row_i_col_j_card_xpath)[0]

                    # get card data / no lines check
                    no_lines = False
                    try:
                        row_i_col_j_card_data_xpath = ".//div[@data-action-type='deeplink']"
                        row_i_col_j_card_data = row_i_col_j_card.xpath(row_i_col_j_card_data_xpath)[0]
                        row_i_col_j_odds_xpath = ".//div[@class='d-flex justify-content-between align-items-center']"
                        row_i_col_j_odds = row_i_col_j_card_data.xpath(row_i_col_j_odds_xpath)[0].text
                    except Exception:
                        row_i_col_j_odds = 'No Lines'
                        no_lines = True

                    if no_lines:
                        odds = data.OddsBySite(self.lines_and_sportsbooks[line_index], row_i_col_j_odds)
                        curr_event.players[player_index].odds.append(odds)
                        self.data.rows.append(
                            data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                          curr_event.players[player_index].player_name, odds.site_name, odds.odds))

                    # get best line sportsbook
                    elif best_line:
                        try:
                            image_xpath = ".//img[@height='18px' and @width='18px']"
                            url = row_i_col_j_card_data.xpath(image_xpath)[0]
                            sportsbook = self.lines_and_sportsbooks[line_index] + ': ' + parse_image_url(url)
                            best_line_odds = data.OddsBySite(sportsbook, row_i_col_j_odds)
                        except Exception:
                            best_line_odds = data.OddsBySite(self.lines_and_sportsbooks[line_index], row_i_col_j_odds)
                        curr_event.players[player_index].odds.append(best_line_odds)
                        self.data.rows.append(
                            data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                          curr_event.players[player_index].player_name, best_line_odds.site_name, best_line_odds.odds))

                    # get true line ev
                    elif true_line:
                        try:
                            ev_xpath = ".//div[@style='margin-top:1px;margin-bottom:1px']"
                            ev = row_i_col_j_card.xpath(ev_xpath)[0].text
                            sportsbook = self.lines_and_sportsbooks[line_index] + ': ' + str(ev)
                        except Exception:
                            sportsbook = self.lines_and_sportsbooks[line_index]
                        true_line_odds = data.OddsBySite(sportsbook, row_i_col_j_odds)
                        curr_event.players[player_index].odds.append(true_line_odds)
                        self.data.rows.append(
                            data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                          curr_event.players[player_index].player_name, true_line_odds.site_name, true_line_odds.odds))

                    else:
                        curr_event.players[player_index].odds.append(data.OddsBySite(self.lines_and_sportsbooks[line_index], row_i_col_j_odds))
                        self.data.rows.append(
                            data.TableRow(self.sport.sport_name, curr_market.market_name, curr_event.event_name,
                                          curr_event.players[player_index].player_name, self.lines_and_sportsbooks[line_index], row_i_col_j_odds))

                    line_index += 1

                row_index += 1
                player_index += 1

    def get_csv(self, file_name):
        df = pandas.DataFrame(([table_row.row for table_row in self.data.rows]),
                              columns=['sport', 'market', 'game/event', 'player', 'site', 'odds'])
        df.to_csv(file_name + '.csv', index=False)

    def update_table(self):
        self.__init__(self.sport.sport_name, self.url, self.path)


def parse_image_url(url):
    url = urlparse(url.attrib['src']).path
    url = url.split('_', 1)[1].split('@', 1)[0].split('800', 1)[0].split('384', 1)[0].split('48', 1)[0].split('_', 1)[0].split('.', 1)[0]
    return url


def main():
    url = 'https://labs.actionnetwork.com/markets'
    # sport = 'NBA' OR 'PGA'
    sport = 'NBA'
    # specify path to chromedriver
    path = '/Users/owenmorris/Desktop/chromedriver'
    # create new scraper with sport, url, path
    scraper = SportScraper(sport, url, path)
    # output scraped data as csv
    scraper.get_csv(scraper.sport.sport_name)


if __name__ == "__main__":
    main()

