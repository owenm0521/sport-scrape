# DRIVER

import sport_scraper
import threading


class Repeater:
    def __init__(self, wait_time, function, *args):
        self._timer = None
        self.wait_time = wait_time
        self.function = function
        self.args = args
        self.is_running = False
        self.terminate = False
        self.start()

    def _run(self):
        self.is_running = False
        thread = threading.Thread(target=self.function(*self.args))
        thread.start()
        thread.join()
        self.start()

    def start(self):
        if not self.is_running and not self.terminate:
            self._timer = threading.Timer(self.wait_time, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.terminate = True
        self.is_running = False


def run_scrape(scraper, csv_file_name):
    scraper.get_csv(csv_file_name)
    print('Table Updated')
    scraper.update_table()


def main():
    url = 'https://labs.actionnetwork.com/markets'
    # sport = 'NBA' OR 'PGA'
    sport = 'PGA'
    # specify path to chromedriver
    path = '/Users/owenmorris/Desktop/chromedriver'
    csv_file_name = sport
    wait_time = int(input("Run every x seconds: "))
    print("Type 'stop' to terminate.")
    scraper = sport_scraper.SportScraper(sport, url, path)
    r = Repeater(wait_time, run_scrape, scraper, csv_file_name)
    while True:
        user_input = input()
        if user_input == 'stop':
            r.stop()
            break


if __name__ == "__main__":
    main()






