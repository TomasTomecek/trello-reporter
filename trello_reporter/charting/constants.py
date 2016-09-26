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


# help messages in UI

BURNDOWN_CHART_DESCRIPTION = "This chart is..."
CONTROL_CHART_DESCRIPTION = "This chart is..."
VELOCITY_CHART_DESCRIPTION = "This chart is..."
CUMULATIVE_FLOW_CHART_DESCRIPTION = "This chart is..."
SPRINT_COMMITMENT_DESCRIPTION = "Columns which..."
DATA_SYNCHRONIZATION_DESCRIPTION = "Data are synchronized..."
SPRINT_CALCULATION_DESCRIPTION = "Sprints are calculated..."
SELECTED_COLUMNS_DESCRIPTION = "Filter..."
