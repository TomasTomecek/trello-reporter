# date time format used everywhere, TZ is important so users know that it's localized
DATETIME_FORMAT = '%Y-%m-%d %H:%M %Z'

# final card state in a sprint
COMPLETED_COLUMNS = ["Complete", "Accepted"]

# columns used to compute sprint commitment
SPRINT_COMMITMENT_COLUMNS = ["Next", "In Progress"]

# initial columns we usually care about
INITIAL_COLUMNS = ["New", "Backlog", "Next", "In Progress", "Complete"]

# initial is good enough
CUMULATIVE_FLOW_INITIAL_WORKFLOW = INITIAL_COLUMNS
