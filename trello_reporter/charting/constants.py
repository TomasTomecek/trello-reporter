# date time format used everywhere, TZ is important so users know that it's localized
DATETIME_FORMAT = '%Y-%m-%d %H:%M %Z'

# final card state in a sprint
COMPLETED_COLUMNS = ["Complete", "Accepted"]

# columns for sprint cards which indicate active sprint
SPRINT_CARDS_ACTIVE = ["In Progress", "Next"]

# columns used to compute sprint commitment
SPRINT_COMMITMENT_COLUMNS = ["Next", "In Progress"]

# initial columns we usually care about
INITIAL_COLUMNS = ["New", "Backlog", "Next", "In Progress", "Complete"]

# initial is good enough
CUMULATIVE_FLOW_INITIAL_WORKFLOW = INITIAL_COLUMNS

# maximum number of story points a card can have
MAX_STORY_POINTS = 21

# help messages in UI
BURNDOWN_CHART_DESCRIPTION = "A burndown chart is a graphical representation of work left to do versus time. On vertical axis is number of story points, on horizontal axis time. Reporter is showing ideal green line, while blue line shows actual progress of burned cards, which are also shown as blue column going up from horizontal axis. This chart doesn't have to be the right one for you project especially if you are not using story points or if your team is working more in kanban style."
CONTROL_CHART_DESCRIPTION = "The control chart is a graph used to study how a process changes over time. Data are plotted in time order. Don't forget to define you workflow according to Trello. Number of days are calculated from the first day a card reached the designated column (the one you set in the workflow as first). If cards are moved to In Progress, Next or other is not stopping the calculation. The calculation is stopped when the card reaches the Complete column."
VELOCITY_CHART_DESCRIPTION = "Velocity is a measurement of how much the team gets done in a sprint. Velocity is what actually got done in the last iteration not what was planned. You can pick how many sprints you want to see and take into counting the average. The green line shows average based on number of sprints, blue columns are for done and committed. "
CUMULATIVE_FLOW_CHART_DESCRIPTION = "The Cumulative Flow Diagram (CFD) is a great tool for tracking and forecasting projects. You can tell where bottlenecks are. In Reporter you can set usage of cards or story points based on your workflow."
SPRINT_COMMITMENT_DESCRIPTION = "Velocity and burndown chart are using these commitment data. Usually Next column. It is important to add cards into Next column, say we are committed to these cards. And then scrum master will create card with name Sprint number_of_sprint in In Progress column. This card must contain due date, which is the same as end of the sprint. From these data is taken length of the sprint. If you did something wrong, data might be skewed and you need to setup manually dates in charts."
DATA_SYNCHRONIZATION_DESCRIPTION = "Data are synchronized once a day. You need to hit refresh button if you've changed data on your board. It can take a really long time based on number of cards on your board."
SPRINT_CALCULATION_DESCRIPTION = "Sprints are automatically generated based on the card Sprint number e.g. Sprint 1. The card must be created and added into the In Progress column at the end of planning. Card must contain Due Date, which defines end of the sprint. At the end of the sprint, the card needs to move into the Complete column. Do not rename the card and re-use it. The length of a sprint is not precise, because it guesstimated. If you pick the sprint e.g. Sprint 7, you can choose Start date and End date manually, even the hour!"
SELECTED_COLUMNS_DESCRIPTION = "These columns can help you understand what is happening with your cards for example if some are stalled. At the top you can see From/To dates, which you can use for picking up an interesting time interval. The chart above shows you growth of number of cards and story points. You can usually say when planning was happening and found out if your backlog is constantly growing. Card are listed according time of creation. The newest are on the top. You can check what was the last action, when (check if it shows your timezone), number of cards in the column and number of story points in the column."
