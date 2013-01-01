from setuptools import setup, find_packages

long_description='Search shoutcast.com for radio stations (not for commercial use, see http://forums.winamp.com/showthread.php?threadid=295638). Use criteria to search for station names, genres or current songs, and filters to specify details. Keywords are used to search freely among station names, genres and current songs. With no criteria or keywords, %prog returns the current Top500 list. Stations can be sorted in different ways using sorters. Example: \'%prog -n 10 -g Rock -p "Depeche Mode" -b "=128"\' shows the top ten Rock 128kbps stations currently playing Depeche Mode.'

setup(
    name = 'shoutcast_search',
    version = '0.4.1',
    url = 'http://github.com/halhen/shoutcast-search',
    author = 'Henrik Hallberg',
    author_email = 'halhen@k2h.se',
    license = 'GPL',
    packages = find_packages(),
    install_requires = ['setuptools'],
    description = 'Search shoutcast.com web radio stations',
    long_description = long_description,
    classifiers = [
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        ],
    entry_points = {'console_scripts':['shoutcast-search=shoutcast_search.shoutcast_search:main']},
    )
