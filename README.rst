Screenshots:
============

.. image:: https://github.com/rbreu/gcode-tracker-graphs/raw/master/screenshots/open_issues.png

.. image:: https://github.com/rbreu/gcode-tracker-graphs/raw/master/screenshots/opened_closed_issues.png


Prerequisites:
==============

* Python >= 2.6
* Matplotlib
* The Gcode python API


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

