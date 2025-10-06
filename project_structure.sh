#!/bin/bash

# Create main directories
mkdir -p services/master_bot/src
mkdir -p services/producer/src
mkdir -p services/consumer/src
mkdir -p services/notifier/src
mkdir -p services/feedback_processor/src
mkdir -p common/models
mkdir -p common/database
mkdir -p common/messaging

# Create empty __init__.py files to make directories importable
touch services/master_bot/src/__init__.py
touch services/producer/src/__init__.py
touch services/consumer/src/__init__.py
touch services/notifier/src/__init__.py
touch services/feedback_processor/src/__init__.py
touch common/__init__.py
touch common/models/__init__.py
touch common/database/__init__.py
touch common/messaging/__init__.py
