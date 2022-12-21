from datetime import datetime, timedelta

TODAY = datetime.today()
YESTERDAY = TODAY - timedelta(days=1)

INTERACTIVE_ANSWERS = ['Y', 'y', 'YES',
                       'Yes', 'yes', 'N', 'n', 'NO', 'No', 'no']

YES_ANSWERS = INTERACTIVE_ANSWERS[:5]
NO_ANSWERS = INTERACTIVE_ANSWERS[5:]
