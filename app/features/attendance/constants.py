from datetime import date

# Check-in deduction assumes the morning shift starts at 08:00 until per-user
# schedules exist.
WORK_START_MINUTES = 8 * 60

# Missed check-ins are counted from the Asia/Ho_Chi_Minh go-live date, inclusive.
MISS_CHECK_IN_COUNTING_START = date(2026, 11, 18)
