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
import sys
import re
from os.path import expanduser

from config import conf


def init_db():
    conn = sqlite3.connect(expanduser("~/.gcode_tracker_graphs.sqlite"))
    cursor = conn.cursor()

    if conf["cache"] == "none":
        cursor.execute("DELETE FROM %s" % (conf["project"],))
    elif conf["cache"] == "closed":
        cursor.execute("DELETE FROM %s WHERE closed=0" % (conf["project"],))
    else:
        pass

    
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

    if len(comments) == 25:
        logging.warning("Reached limit of 25 comments.")

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
    next_retry = 0
    same_retry = 0
    cursor = db.cursor()

    i = 1

    while True:

        # Do we already have info about this issue?
        cursor.execute("SELECT COUNT(*) FROM %s where ROWID=?"
                       % (conf["project"],), (i,))
        if cursor.fetchall()[0][0] > 0:
            logging.debug("Issue %s exists in cache. Skipping." % (i,))
            i += 1
            continue

        # Get the issue from Gcode
        query = gdata.projecthosting.client.Query(issue_id=i, max_results=1)
        
        try:
            feed = client.get_issues(conf["project"], query=query)
            comments_feed = client.get_comments(conf["project"], i)
        except gdata.client.RequestError, e:
            if re.match("Server responded with: (403|404)", e.message):
                # this issue is inaccessible, try the next one
                logging.warning(e.message)
                if next_retry > conf["next_retry"]:
                    logging.warning("Issue %i: Giving up." % (i,))
                    break
                else:
                    logging.warning("Issue %i: Skipping." % (i,))
                    i += 1
                    next_retry += 1
                    continue
            elif re.match("Server responded with: (500)", e.message):
                # try this issue again
                if  same_retry > conf["same_retry"]:
                    logging.warning(e.message)
                    logging.warning("Issue %i: Giving up." % (i,))
                    i += 1
                    continue
                else:
                    logging.debug(e.message)
                    logging.debug("Issue %i: Trying again." % (i,))
                    same_retry += 1
                    continue
            else:
                raise
        
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

        next_retry = 0
        same_retry = 0
        i += 1

        
    cursor.execute("SELECT COUNT(*) FROM %s" % (conf["project"],))
    count_all =  cursor.fetchall()[0][0]
    cursor.execute("SELECT COUNT(*) FROM %s WHERE closed=0" % (conf["project"],))
    count_open =  cursor.fetchall()[0][0]
    logging.info("Found %s issues total, %s open." % (count_all, count_open))
    db.commit()


def prepare_data_for_plot(db):
    cursor = db.cursor()
    
    logging.info("Preparing data for plotting...")
    cursor.execute("SELECT DATE(MIN(opened)) FROM %s" % conf["project"],)
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
        cursor.execute("SELECT COUNT(*) FROM %s WHERE DATE(opened)=?" %
                       (conf["project"],),
                       (date.strftime("%Y-%m-%d"),))
        opened = cursor.fetchall()[0][0]

        cursor.execute("SELECT COUNT(*) FROM %s WHERE DATE(closed)=?" %
                       (conf["project"],),
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


def annotate_plot(ax, dates, data):
    if not conf["annotations"]:
        return ax

    maxdata = max(data)
    
    for (text, date) in conf["annotations"]:
        logging.debug("Annotating %s: %s" % (date, text))
        x = mdates.date2num(datetime.strptime(date, "%Y-%m-%d"))
        y = max(data[dates.index(x)], 0.1)
        if y > maxdata/2:
            ytext = maxdata/5
            align = "bottom"
        else:
            ytext = maxdata*4/5
            align = "top"

        ax.annotate(text, (x, y), xytext=(x, ytext), rotation=-90,
                    verticalalignment = align,
                    horizontalalignment = "center",
                    arrowprops=dict(arrowstyle="-", connectionstyle="arc3"),)

    return ax
        

def plot(opened_issues, closed_issues, open_issues, dates):
    logging.info("Plotting to file %s ..." % (conf["open_issues_outfile"],))
    
    figure = pyplot.figure()
    ax = figure.gca()
    ax.plot_date(dates, open_issues, linestyle="-", marker='None', color='red')
    ax = annotate_plot(ax, dates, open_issues)
    ax.xaxis.set_major_locator(mdates.MonthLocator(range(1, 12 ,2)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
    figure.autofmt_xdate(rotation=45)
    figure.suptitle("Number of open issues")
    figure.savefig(conf["open_issues_outfile"])

    logging.info("Plotting to file %s ..." % (conf["opened_closed_issues_outfile"],))
    figure = pyplot.figure()
    ax = figure.gca()
    ax.plot_date(dates, opened_issues, linestyle="-", marker='None',
                 label="Opened issues", color='red')
    ax.plot_date(dates, closed_issues, linestyle="-", marker='None',
                 label="Closed issues", color='blue')
    ax = annotate_plot(ax, dates, closed_issues)
    ax.xaxis.set_major_locator(mdates.MonthLocator(range(1, 12 ,2)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
    ax.legend()
    figure.autofmt_xdate(rotation=45)
    figure.suptitle("Number of issues opened/closed per day")
    figure.savefig(conf["opened_closed_issues_outfile"])



if __name__ == "__main__":

    try:
        project = sys.argv[1]
    except IndexError:
        print "Usage: gcode_tracker_graphs.py <projectname>"
        sys.exit(1)
        
    conf.load_from_file(project)
    logging.basicConfig(level=getattr(logging, conf["loglevel"]))
    
    db = init_db()
    
    logging.info("Connecting to gcode...")
    client = gdata.projecthosting.client.ProjectHostingClient()
    client.ClientLogin(conf["user"], conf["password"],
                       source="otwarchive-graphs")

    get_all_issues(client, db)
    plot(*prepare_data_for_plot(db))

    db.close()
