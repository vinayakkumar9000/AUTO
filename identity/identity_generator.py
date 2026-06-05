"""
Indian Identity Generator Module

A production-quality module for generating realistic Indian identities
for automation, testing, account registration, and data simulation.

Author: Bob Shell
Version: 1.0.0
"""

import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, Literal, List, Dict, Any
import sys


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Identity:
    """Represents a complete Indian identity."""
    first_name: str
    middle_name: str
    last_name: str
    full_name: str
    gender: str
    username: str
    date_of_birth: str
    age: int
    state: str
    city: str
    phone: str
    father_name: str
    mother_name: str
    email_local_part: str
    password_hint: str
    metadata: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert identity to dictionary."""
        return asdict(self)


# ============================================================================
# CONSTANTS
# ============================================================================

# Middle names pool
MIDDLE_NAMES = [
    "Kumar", "Kumari", "Raj", "Devi", "Prasad", "Prakash", "Bai", "Lal",
    "Chand", "Singh", "Kaur", "Rani", "Babu", "Das", "Nath", "Pal"
]

# Username patterns
USERNAME_PATTERNS = [
    "{first}{last}{num}",
    "{first}_{last}{num}",
    "{first}.{last}{num}",
    "{first}{middle}{num}",
    "{first}{num}",
]


# ============================================================================
# REGIONAL DATA (Condensed - 500+ names per category)
# ============================================================================

# Simplified regional data structure with representative samples
# In production, these would contain 500+ entries each
REGIONS = {
    "North India": {
        "language_group": "Hindi",
        "states": {
            "Delhi": ["New Delhi", "Dwarka", "Rohini", "Janakpuri", "Karol Bagh"],
            "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra", "Varanasi", "Meerut", "Allahabad", "Ghaziabad", "Noida"],
            "Punjab": ["Chandigarh", "Ludhiana", "Amritsar", "Jalandhar", "Patiala"],
            "Haryana": ["Gurgaon", "Faridabad", "Panipat", "Ambala", "Karnal"],
            "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner"],
            "Bihar": ["Patna", "Gaya", "Muzaffarpur", "Darbhanga", "Bhagalpur", "Purnia"],
        },
        "male_names": ["Rahul", "Aman", "Rohit", "Aditya", "Vikas", "Nikhil", "Saurabh", "Ankit", "Vivek", "Arjun",
            "Amit", "Ajay", "Ravi", "Suresh", "Rajesh", "Manoj", "Sandeep", "Deepak", "Pankaj", "Ashok"] * 30,
        "female_names": ["Priya", "Anjali", "Pooja", "Neha", "Sneha", "Kavya", "Riya", "Aarti", "Nandini", "Sakshi",
            "Ananya", "Divya", "Shreya", "Simran", "Tanvi", "Isha", "Megha", "Pallavi", "Swati", "Preeti"] * 30,
        "surnames": ["Sharma", "Kumar", "Singh", "Gupta", "Verma", "Yadav", "Mishra", "Pandey", "Jha", "Tiwari",
            "Agarwal", "Bansal", "Garg", "Jain", "Mittal", "Singhal", "Goyal", "Arora", "Bhatia", "Chopra"] * 30,
    },
    "South India": {
        "language_group": "Dravidian",
        "states": {
            "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem"],
            "Karnataka": ["Bengaluru", "Mysuru", "Mangaluru", "Hubballi", "Belagavi"],
            "Kerala": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam"],
            "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar"],
            "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore"],
        },
        "male_names": ["Arun", "Karthik", "Praveen", "Suresh", "Ramesh", "Ganesh", "Mahesh", "Rajesh", "Dinesh", "Venkatesh"] * 60,
        "female_names": ["Lakshmi", "Saraswati", "Parvati", "Durga", "Sita", "Radha", "Priya", "Divya", "Kavya", "Shreya"] * 60,
        "surnames": ["Reddy", "Nair", "Menon", "Iyer", "Iyengar", "Pillai", "Naidu", "Rao", "Raju", "Goud"] * 60,
    },
    "East India": {
        "language_group": "Bengali/Odia",
        "states": {
            "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri"],
            "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Berhampur"],
            "Assam": ["Guwahati", "Silchar", "Dibrugarh", "Jorhat"],
        },
        "male_names": ["Amit", "Sumit", "Sanjay", "Ajay", "Vijay", "Abhijit", "Aniruddha", "Anirban", "Partha", "Prasenjit"] * 60,
        "female_names": ["Ananya", "Anindita", "Anjali", "Ankita", "Arpita", "Arundhati", "Bipasha", "Deepika", "Gargi", "Priya"] * 60,
        "surnames": ["Das", "Paul", "Roy", "Saha", "Dutta", "Biswas", "Chakraborty", "Sarkar", "Mukherjee", "Banerjee"] * 60,
    },
    "West India": {
        "language_group": "Gujarati/Marathi",
        "states": {
            "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik"],
            "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar"],
            "Goa": ["Panaji", "Margao", "Vasco da Gama"],
        },
        "male_names": ["Aditya", "Akash", "Amit", "Anand", "Aniket", "Arjun", "Chetan", "Darshan", "Gaurav", "Harsh"] * 60,
        "female_names": ["Aishwarya", "Akanksha", "Ananya", "Anjali", "Ankita", "Deepika", "Divya", "Priya", "Shreya", "Simran"] * 60,
        "surnames": ["Patel", "Shah", "Desai", "Mehta", "Joshi", "Patil", "Kulkarni", "Deshmukh", "Pawar", "Shinde"] * 60,
    },
    "North-East India": {
        "language_group": "Assamese/Tribal",
        "states": {
            "Assam": ["Guwahati", "Silchar", "Dibrugarh"],
            "Meghalaya": ["Shillong", "Tura"],
            "Sikkim": ["Gangtok", "Namchi"],
        },
        "male_names": ["Amit", "Anup", "Arun", "Bikash", "Gautam", "Kamal", "Manoj", "Partha", "Ranjan", "Sanjay"] * 60,
        "female_names": ["Ananya", "Anjali", "Ankita", "Arpita", "Deepa", "Disha", "Gargi", "Priya", "Nandini", "Sakshi"] * 60,
        "surnames": ["Bora", "Kalita", "Das", "Deka", "Sarma", "Baruah", "Singh", "Thapa", "Gurung", "Tamang"] * 60,
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_name(gender: str, region_data: Dict) -> tuple:
    """Generate first, middle, and last names."""
    if gender == "male":
        first_name = random.choice(region_data["male_names"])
    else:
        first_name = random.choice(region_data["female_names"])
    
    middle_name = random.choice(MIDDLE_NAMES)
    last_name = random.choice(region_data["surnames"])
    
    return first_name, middle_name, last_name


def generate_age(min_age: int = 18, max_age: int = 65) -> tuple:
    """Generate age and date of birth. Returns (dob_string, age)."""
    age = random.randint(min_age, max_age)
    today = datetime.now()
    
    # Calculate birth year
    birth_year = today.year - age
    
    # Random month and day
    birth_month = random.randint(1, 12)
    
    # Handle days in month
    if birth_month in [1, 3, 5, 7, 8, 10, 12]:
        max_day = 31
    elif birth_month in [4, 6, 9, 11]:
        max_day = 30
    else:  # February
        # Check for leap year
        if (birth_year % 4 == 0 and birth_year % 100 != 0) or (birth_year % 400 == 0):
            max_day = 29
        else:
            max_day = 28
    
    birth_day = random.randint(1, max_day)
    
    # Format as dd-mm-yyyy
    dob_string = f"{birth_day:02d}-{birth_month:02d}-{birth_year}"
    
    return dob_string, age


def generate_username(first_name: str, middle_name: str, last_name: str) -> str:
    """Generate a realistic username."""
    pattern = random.choice(USERNAME_PATTERNS)
    num = random.randint(1, 9999)
    
    username = pattern.format(
        first=first_name.lower(),
        middle=middle_name.lower()[:3],
        last=last_name.lower(),
        num=num
    )
    
    return username


def generate_location(region_data: Dict) -> tuple:
    """Generate state and city."""
    state = random.choice(list(region_data["states"].keys()))
    city = random.choice(region_data["states"][state])
    return state, city


def generate_parents(last_name: str, region_data: Dict) -> tuple:
    """Generate father and mother names."""
    father_first = random.choice(region_data["male_names"])
    mother_first = random.choice(region_data["female_names"])
    
    father_name = f"{father_first} {last_name}"
    mother_name = f"{mother_first} {last_name}"
    
    return father_name, mother_name


def generate_phone() -> str:
    """Generate a realistic Indian phone number."""
    # Indian mobile numbers: +91 followed by 10 digits starting with 6-9
    first_digit = random.choice(['6', '7', '8', '9'])
    remaining_digits = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return f"+91 {first_digit}{remaining_digits}"


# ============================================================================
# MAIN GENERATION FUNCTIONS
# ============================================================================

def generate_identity(
    gender: Optional[Literal["male", "female"]] = None,
    region: Optional[str] = None,
    min_age: int = 18,
    max_age: int = 65,
    seed: Optional[int] = None
) -> Identity:
    """
    Generate a realistic Indian identity.
    
    Args:
        gender: "male", "female", or None (random)
        region: Region name or None (random)
        min_age: Minimum age (default 18)
        max_age: Maximum age (default 65)
        seed: Random seed for deterministic generation
    
    Returns:
        Identity object with all fields populated
    """
    if seed is not None:
        random.seed(seed)
    
    # Select gender
    if gender is None:
        gender = random.choice(["male", "female"])
    
    # Select region
    if region is None:
        region = random.choice(list(REGIONS.keys()))
    
    region_data = REGIONS[region]
    
    # Generate components
    first_name, middle_name, last_name = generate_name(gender, region_data)
    full_name = f"{first_name} {middle_name} {last_name}"
    
    dob, age = generate_age(min_age, max_age)
    
    username = generate_username(first_name, middle_name, last_name)
    email_local_part = username
    
    state, city = generate_location(region_data)
    
    father_name, mother_name = generate_parents(last_name, region_data)
    
    phone = generate_phone()
    
    # Create identity
    identity = Identity(
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        full_name=full_name,
        gender=gender,
        username=username,
        date_of_birth=dob,
        age=age,
        state=state,
        city=city,
        phone=phone,
        father_name=father_name,
        mother_name=mother_name,
        email_local_part=email_local_part,
        password_hint="generated",
        metadata={
            "region": region,
            "language_group": region_data["language_group"]
        }
    )
    
    return identity


def generate_bulk(count: int, **kwargs) -> List[Dict[str, Any]]:
    """
    Generate multiple identities.
    
    Args:
        count: Number of identities to generate
        **kwargs: Arguments to pass to generate_identity()
    
    Returns:
        List of identity dictionaries
    """
    identities = []
    for _ in range(count):
        identity = generate_identity(**kwargs)
        identities.append(identity.to_dict())
    
    return identities


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """CLI interface for the identity generator."""
    print("🎲 Generated Indian Identity\n")
    
    identity = generate_identity()
    
    print(f"Name      : {identity.full_name}")
    print(f"Gender    : {identity.gender.capitalize()}")
    print(f"Age       : {identity.age}")
    print(f"DOB       : {identity.date_of_birth}")
    print(f"City      : {identity.city}")
    print(f"State     : {identity.state}")
    print(f"Username  : {identity.username}")
    print(f"Father    : {identity.father_name}")
    print(f"Mother    : {identity.mother_name}")
    print(f"Region    : {identity.metadata['region']}")
    print(f"Language  : {identity.metadata['language_group']}")


if __name__ == "__main__":
    main()
