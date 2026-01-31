# Donation Routing System

A centralized platform connecting donors with verified NGOs to ensure transparent and efficient donation routing in Karachi.

---

## Table of Contents

1. [Project Overview](#project-overview)  
2. [Features](#features)  
3. [Technologies Used](#technologies-used)  
4. [Project Structure](#project-structure)  
5. [Screenshots](#screenshots)  
6. [Setup & Installation](#setup--installation)  
7. [Usage](#usage)  
8. [Future Improvements](#future-improvements)  
9. [Contributing](#contributing)  
10. [License](#license)  

---

## Project Overview

The **Donation Routing System** is a web-based platform designed to streamline the donation process by connecting donors with verified NGOs. It ensures that donations are routed transparently and efficiently, allowing donors to track their contributions in real-time.

Key Goals:  

- Provide an intuitive interface for donors to submit and track donations.  
- Enable administrators to manage NGOs, donations, and routing decisions.  
- Display verified NGOs with details such as category, location, current needs, and pickup options.  

---

## Features

### Donor Portal
- Register as a new donor or login as an existing donor.
- Submit donations and view the donation history.
- Track donations using a unique tracking ID.
- View a list of available NGOs and their details.

### Admin Portal
- Login as an administrator to manage system operations.
- Approve, reject, or assign donations to NGOs.
- Manage NGO details and their current needs.

### NGO Management
- Display verified NGOs with name, category, location, accepted items, and pickup availability.
- Admins can manage the needs of each NGO.

### Donation Tracking
- Real-time donation status updates:
  - Pending  
  - Assigned  
  - Rejected  
- Show assigned NGO details for approved donations.
- Progress tracker for easy visual representation.

---

## Technologies Used

- **Backend:** Python, Flask  
- **Frontend:** HTML, CSS, Jinja2 templates  
- **Database:** SQLite / SQLAlchemy  
- **Styling:** Custom CSS with reusable card components  
- **Others:** FontAwesome for icons  

---

## Project Structure
```
donation-routing-system/
│
├── templates/
│ ├── base.html # Main layout template
│ ├── donor_home.html # Donor home page
│ ├── donor_ngos.html # List of NGOs for donors
│ ├── list_ngos.html # List of NGOs with table view
│ ├── login.html # Donor/Admin login page
│ ├── register.html # Donor registration page
│ ├── track_form.html # Form to track donation
│ └── track_result.html # Donation status display
│
├── static/
│ ├── css/ # Custom styles
│ └── js/ # Optional JS scripts
│
├── app.py # Flask main application
├── models.py # Database models
└── README.md # Project documentation
```


## Setup & Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/donation-routing-system.git
cd donation-routing-system
```
2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run the Flask app**

```bash
export FLASK_APP=app.py       # Linux/Mac
set FLASK_APP=app.py          # Windows
flask run
```

5. **Open in browser**

```bash
http://127.0.0.1:5000/
```

## Usage

1. Navigate to the Donor Home Page.
2. Register as a new donor or login if already registered.
3. Submit donations via the Donor Portal.
4. Track your donations using the Tracking ID.
5. Admins can login to manage NGOs, donations, and routing decisions.
6. View all verified NGOs and their current needs.

## Future Improvements

- Add email notifications for donation status updates.
- Enable multi-city support beyond Karachi.
- Implement real-time analytics for admins.
- Add user profile dashboards for donors.
- Integrate with payment gateways for monetary donations.

## Contributing

1. Fork the repository.
2. Create a feature branch: ```git checkout -b feature-name```
3. Commit your changes: ```git commit -m "Add feature" ```
4. Push to the branch: ```git push origin feature-name```
5. Open a Pull Request.

