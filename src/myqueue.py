from queue import Queue
from main import scrape_day_court_cases
from utils import date_range, accept_terms_and_conditions
from threading import Thread
from datetime import date, time


start_time = time.time()

# Create a queue and fill it
# start_date = "01/01/2020"
# end_date = "01/15/2020"
start_date = date(2022, 1, 1)
end_date = date(2022, 2, 1)
dates = list(date_range(start_date, end_date))


session = accept_terms_and_conditions()

def scraper_worker(q):
    while not q.empty():
        date = q.get()
        # prepare_csv_file_location(date)
        scrape_day_court_cases(date, session)
        q.task_done()

q = Queue()
list(map(q.put, dates))

for i in range(4):
    # t = Thread(target=scrape_day_court_cases, args=(q, ))
    t = Thread(target=scraper_worker, args=(q, ))
    t.start()
q.join()
