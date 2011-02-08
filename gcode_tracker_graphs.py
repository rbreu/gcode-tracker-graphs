#!/usr/bin/env python

"""
This file is part of gcode-tracker-graphs.

gcode-tracker-graphs is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

gcode-tracker-graphs is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with gcode-tracker-graphs. If not, see <http://www.gnu.org/licenses/>.

Copyright 2011 Rebecca Breu
"""

import gdata.projecthosting.client
import logging
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as pyplot
import matplotlib.dates as mdates
from os.path import expanduser
import sys
import imp


def init_db():
    conn = sqlite3.connect(expanduser("~/.gcode_tracker_graphs.sqlite"))
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS %s
                     (opened REAL,
                      closed REAL DEFAULT 0)""" % (conf["project"],))
    conn.commit()
    return conn


def get_closed_date(comments):
    """
    If an issue has set to a closed status without having been
    reopend, take the first close date. If it has been reopened from a
    closed date, take the last close date. It's then considered to
    have been open all the time.
    """
    date = None

    for comment in comments:
        if date is None:
            for close_string in conf["closed"]:
                if close_string in str(comment.updates):
                    date = comment.published.text
        else:
            for open_string in conf["open"]:
                if open_string in str(comment.updates):
                    date = None
                
    return date


def get_all_issues(client, db):
    logging.info("Collecting issues...")
    retry = 0
    cursor = db.cursor()

    i = 0

    while True:
        i += 1

        # Do we already have info about this issue?
        cursor.execute("SELECT COUNT(*) FROM %s where ROWID=?"
                       % (conf["project"],), (i,))
        if cursor.fetchall()[0][0] > 0:
            logging.debug("Issue %s exists in cache. Skipping." % (i,))
            continue

        # Get the issue from Gcode
        query = gdata.projecthosting.client.Query(issue_id=i, max_results=1)
        
        try:
            feed = client.get_issues(conf["project"], query=query)
            comments_feed = client.get_comments(conf["project"], i)
        except gdata.client.RequestError:
            if retry > 5:
                logging.warning("Issue %s not found. Giving up." % (i,))
                break
            else:
                logging.warning("Issue %s not found. Trying next." % (i,))
                retry += 1
                continue
        
        issue = feed.entry[0]

        closed_date = get_closed_date(comments_feed.entry)
        if closed_date:
            logging.debug("Issue %s opened at %s closed at %s" %
                          (i, issue.published.text, closed_date))
            cursor.execute("INSERT INTO %s (ROWID,opened,closed) VALUES (?,?,?)"
                           % (conf["project"],),
                           (i, issue.published.text, closed_date))
        else:
            logging.debug("Issue %s opened at %s still open" %
                          (i, issue.published.text))
            cursor.execute("INSERT INTO %s (ROWID,opened) VALUES (?,?)"
                           % (conf["project"],),
                           (i, issue.published.text,))

        retry = 0
        
    cursor.execute("SELECT COUNT(*) FROM %s" % (conf["project"],))
    count_all =  cursor.fetchall()[0][0]
    cursor.execute("SELECT COUNT(*) FROM %s WHERE closed=0" % (conf["project"],))
    count_open =  cursor.fetchall()[0][0]
    logging.info("Found %s issues total, %s open." % (count_all, count_open))
    db.commit()


def prepare_data_for_plot(db):
    cursor = db.cursor()
    
    logging.info("Preparing data for plotting...")
    cursor.execute("SELECT DATE(MIN(opened)) FROM issues")
    start_date =  cursor.fetchall()[0][0]
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.today()
    logging.debug("Dates from %s to %s" % (start_date, end_date))

    opened_issues = []
    closed_issues = []
    open_issues = []
    dates = []
    open_count = 0
    date = start_date
    delta = timedelta(days=1)
    
    while date < end_date:
        cursor.execute("SELECT COUNT(*) FROM issues WHERE DATE(opened)=?",
                   (date.strftime("%Y-%m-%d"),))
        opened = cursor.fetchall()[0][0]

        cursor.execute("SELECT COUNT(*) FROM issues WHERE DATE(closed)=?",
                   (date.strftime("%Y-%m-%d"),))
        closed = cursor.fetchall()[0][0]
        open_count = open_count + opened - closed
        logging.debug("On %s: %s opened, %s closed, %s open" %
                      (date, opened, closed, open_count))

        dates.append(mdates.date2num(date))
        opened_issues.append(opened)
        closed_issues.append(closed)
        open_issues.append(open_count)

        date += delta

    return opened_issues, closed_issues, open_issues, dates


def plot(opened_issues, closed_issues, open_issues, dates):
    logging.info("Plotting to file %s ..." % (OPEN_ISSUES_OUTFILE,))
    
    figure = pyplot.figure()
    ax = figure.gca()
    ax.plot_date(dates, open_issues, linestyle="-", marker='None', color='red')
    ax.xaxis.set_major_locator(mdates.MonthLocator(range(1, 12 ,3)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
    figure.savefig(OPEN_ISSUES_OUTFILE)

    logging.info("Plotting to file %s ..." % (OPENED_CLOSED_ISSUES_OUTFILE,))
    figure = pyplot.figure()
    ax = figure.gca()
    ax.plot_date(dates, opened_issues, linestyle="-", marker='None',
                 label="Opened issues", color='red')
    ax.plot_date(dates, closed_issues, linestyle="-", marker='None',
                 label="Closed issues", color='blue')
    ax.xaxis.set_major_locator(mdates.MonthLocator(range(1, 12 ,3)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
    ax.legend()
    figure.savefig(OPENED_CLOSED_ISSUES_OUTFILE)



if __name__ == "__main__":

    project = sys.argv[1]
    _ = imp.load_source("_", expanduser("~/.gcode_tracker_graphs.conf"))
    global conf
    conf = getattr(_, project)
    conf["project"] = project
    
    logging.basicConfig(level=getattr(logging, conf["loglevel"]))
    
    db = init_db()
    
    logging.info("Connecting to gcode...")
    client = gdata.projecthosting.client.ProjectHostingClient()
    client.ClientLogin(conf["user"], conf["password"],
                       source="otwarchive-graphs")

    get_all_issues(client, db)
    plot(*prepare_data_for_plot(db))

    db.close()
