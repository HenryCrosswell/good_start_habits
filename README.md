# This is my README for my habit project

## Big picture
My big picture is that I am bad at sticking to my habits long-term.
Therefore I would like to build the ultimate reminder/ nag-bot.

The end goal will be that if I miss logging a habit by its preset time, a reminder will flash
on an app or PI display screen accordingly, with increasing attention pulling effectivness.
This will stop when I press a button or log that habit.

### Workflow
List of Habits will be stored in Config.

state.json
- To be populated and updated by habits.py

habits.py
- populate state.json with habits, whether it was completed?, and streak count
- day tracker - if more than two days have passed it will reset streak
- day tracker - daily reset app checklists to reset

App.py
- feed information from checklist to habits.py
- recieve streak and reset information from habits.py


To-Do
- write tests for all functions
- implement github actions for CI/CD
