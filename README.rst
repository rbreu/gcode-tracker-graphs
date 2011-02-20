Screenshots:
============

.. image:: https://github.com/rbreu/gcode-tracker-graphs/raw/master/screenshots/open_issues.png

.. image:: https://github.com/rbreu/gcode-tracker-graphs/raw/master/screenshots/opened_closed_issues.png


Prerequisites:
==============

* Python >= 2.6
* Matplotlib
* The Gcode python API


Known Problems:
===============

I haven't found a way to get more than the first 25 comments
(i.e. real comments + label changes + status changes etc.) from an
issue. :( For projects that have lots of issues with many comments,
the graph results will not be very useful.


Usage:
======

Copy gcode_tracker_graphs_conf.py to ~/.gcode_tracker_graphs.conf
and modify it accordingly. It should contain one section (dictionary)
per Gcode project you want to use.

Execute::

  gcode_tracker_graphs.py myproject

Depending on the configuration, the program will cache the issue info
per project in::

  ~/.gcode_tracker_graphs.sqlite


Configuration:
==============

The sample confing file gcode_tracker_graphs_conf.py provides a
commented example showing all configuration options and a minimal
example which will fall back on default options. To view default
options, run::

  config.py
