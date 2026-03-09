# Westway Tennis Booking

A tennis court slot booking system for Westway Sports Centre.

## Features

- Browse available tennis court slots
- Book and manage reservations
- User authentication and profiles
- Admin management interface

## Tech Stack

- **Backend:** Python / Flask
- **Database:** SQLite (development) / PostgreSQL (production)
- **Frontend:** HTML, CSS, JavaScript

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/Raymondli073/Westway_Tennis_Booking.git
cd Westway_Tennis_Booking

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env

# Run the application
flask run
```

## Project Structure

```
Westway_Tennis_Booking/
├── app/                # Application source code
├── tests/              # Test suite
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
└── README.md
```

## Contributing

1. Create a feature branch (`git checkout -b feature/your-feature`)
2. Commit your changes (`git commit -m 'Add your feature'`)
3. Push to the branch (`git push origin feature/your-feature`)
4. Open a Pull Request
