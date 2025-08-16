# Target Saving API Endpoints

This document outlines the API endpoints for the Target Saving feature.

## Feature Overview

The Target Saving feature allows users to create and manage savings goals. Users can set a target amount, a category, and a timeframe for their goals. They can then make deposits towards these goals and track their progress. The system also provides notifications for various events, suchs as creating a new goal, making a deposit, reaching a milestone, and completing a goal.

### Core Functionality

*   **Goal Creation**: Users can create a new savings goal by providing a name, category, target amount, frequency (daily, weekly, or monthly), and start/end dates.
*   **Deposits**: Users can make deposits towards their savings goals. The system automatically updates the current amount and progress percentage.
*   **Progress Tracking**: Users can track the progress of their savings goals through various metrics, including progress percentage, remaining amount, and days remaining.
*   **Notifications**: The system sends notifications for various events, including goal creation, updates, completion, deposits, milestones, and overdue reminders.
*   **Analytics**: The system provides analytics for each savings goal, including total deposits, average deposit amount, and deposit frequency.
*   **Deactivation**: Users can deactivate a savings goal at any time.
*   **Completion**: The system automatically marks a savings goal as complete when the target amount is reached.
# Target Saving API Endpoints

This document outlines the API endpoints for the Target Saving feature.

The base path for all target saving endpoints is `/target-saving/`.

## Target Savings Endpoints

These endpoints are managed by the `TargetSavingViewSet` and are prefixed with `/targets/`.

### Standard CRUD Operations

*   `GET /target-saving/targets/`: List all of the user's target savings.
*   `POST /target-saving/targets/`: Create a new target saving.
*   `GET /target-saving/targets/{target_id}/`: Retrieve a specific target saving.
*   `PUT /target-saving/targets/{target_id}/`: Update a specific target saving.
*   `PATCH /target-saving/targets/{target_id}/`: Partially update a specific target saving.
*   `DELETE /target-saving/targets/{target_id}/`: Delete a specific target saving.

### Custom Actions

*   `GET /target-saving/targets/categories/`: Get a list of available target saving categories.
*   `GET /target-saving/targets/summary/`: Get a summary of the user's target savings.
*   `GET /target-saving/targets/overdue/`: Get a list of overdue target savings.
*   `GET /target-saving/targets/completed/`: Get a list of completed target savings.
*   `GET /target-saving/targets/notifications/`: Get target saving related notifications for the user.
*   `POST /target-saving/targets/send_reminder/`: Send a reminder notification for a specific target saving.
*   `GET /target-saving/targets/{target_id}/details/`: Get detailed information for a specific target saving.
*   `GET /target-saving/targets/{target_id}/analytics/`: Get analytics for a specific target saving.
*   `GET /target-saving/targets/{target_id}/deposits/`: Get all deposits for a specific target saving.
*   `POST /target-saving/targets/{target_id}/deactivate/`: Deactivate a specific target saving.
*   `POST /target-saving/targets/{target_id}/make_deposit/`: Make a deposit to a specific target saving.

## Target Saving Deposits Endpoints

These endpoints are managed by the `TargetSavingDepositViewSet` and are prefixed with `/deposits/`.

### Standard CRUD Operations

*   `GET /target-saving/deposits/`: List all deposits for a user's target savings.
*   `POST /target-saving/deposits/`: Create a new deposit for a target saving.
*   `GET /target-saving/deposits/{deposit_id}/`: Retrieve a specific deposit.
*   `PUT /target-saving/deposits/{deposit_id}/`: Update a specific deposit.
*   `PATCH /target-saving/deposits/{deposit_id}/`: Partially update a specific deposit.
*   `DELETE /target-saving/deposits/{deposit_id}/`: Delete a specific deposit.

### Custom Actions

*   `GET /target-saving/deposits/analytics/`: Get deposit analytics across all of the user's targets.
*   `GET /target-saving/deposits/export_csv/`: Export all target saving deposits to a CSV file.
