
import re
from html import unescape

# ══════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════

def clean_html(text: str) -> str:
    """يشيل tags الـ HTML ويرجع نص نضيف"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def seconds_to_hours(seconds) -> str:
    """يحول الثواني لصيغة 'X.X hours'"""
    if not seconds:
        return ""
    hours = seconds / 3600
    return f"{hours:.1f} hours"


def parse_language(locale) -> str:
   
    if not locale:
        return ""
    if isinstance(locale, dict):
        return (
            locale.get("simpleEnglishTitle")
            or locale.get("title")
            or locale.get("locale")
            or ""
        )
    return str(locale)


def parse_skills(graphql_course: dict, details: dict = None) -> str:
  

   
    if details:
        rest_topics = details.get("topics") or []

      
        if isinstance(rest_topics, list) and len(rest_topics) > 0:
            skills_list = []
            for t in rest_topics:
                if isinstance(t, dict):
                    title = t.get("title", "").strip()
                elif isinstance(t, str):
                    title = t.strip()
                else:
                    title = ""

               
                if title and len(title) <= 40:
                    skills_list.append(title)

            if skills_list:
                return " | ".join(skills_list)

   
    description = ""
    if details:
        description = details.get("description", "") or ""
    if not description:
        description = graphql_course.get("headline", "") or ""

    if description:
        return extract_skills_from_description(description)

    return ""


def extract_skills_from_description(text: str) -> str:
    """
    يستخرج الـ Tech Skills من النص بـ keyword matching
    بيشتغل لو topics فاضي
    """
    if not text:
        return ""

   
    TECH_SKILLS = [
        # Programming Languages
        "Python", "JavaScript", "Java", "C++", "C#", "PHP", "Ruby",
        "Swift", "Kotlin", "TypeScript", "Go", "Rust", "R", "MATLAB",
        "Scala", "Perl", "Dart", "Lua", "Shell", "Bash",

        # Web Frontend
        "HTML", "HTML5", "CSS", "CSS3", "React", "React.js", "Vue",
        "Vue.js", "Angular", "jQuery", "Bootstrap", "Tailwind",
        "Flexbox", "Grid", "SASS", "LESS", "webpack", "Redux",
        "Next.js", "Nuxt.js", "Gatsby", "Svelte",

        # Web Backend
        "Node.js", "Express", "Express.js", "Django", "Flask",
        "FastAPI", "Spring", "Laravel", "Rails", "ASP.NET",
        "GraphQL", "REST", "RESTful", "API", "APIs",

        # Databases
        "SQL", "MySQL", "PostgreSQL", "SQLite", "MongoDB",
        "Redis", "Firebase", "DynamoDB", "Oracle", "NoSQL",
        "Elasticsearch", "Cassandra",

        # Cloud & DevOps
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Linux",
        "Git", "GitHub", "CI/CD", "Jenkins", "Terraform",
        "Ansible", "Nginx", "Apache",

        # Data Science & ML
        "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
        "Keras", "Pandas", "NumPy", "Scikit-learn", "OpenCV",
        "NLP", "Computer Vision", "Data Science", "Data Analysis",
        "Power BI", "Tableau", "Excel",

        # Mobile
        "Android", "iOS", "Flutter", "React Native", "Xamarin",

        # Other
        "Blockchain", "Web3", "Solidity", "NFT",
        "Cybersecurity", "Networking", "EJS", "NPM",
        "Authentication", "OAuth", "JWT",
    ]

    text_lower = text.lower()
    found = []
    seen  = set()

    for skill in TECH_SKILLS:
        skill_lower = skill.lower()
        # بحث دقيق بـ word boundary
        pattern = r'\b' + re.escape(skill_lower) + r'\b'
        if re.search(pattern, text_lower):
            key = skill_lower
            if key not in seen:
                found.append(skill)
                seen.add(key)

    return " | ".join(found) if found else ""


# ══════════════════════════════════════════════════════════
# Main Parser
# ══════════════════════════════════════════════════════════

def parse_course(
    graphql_course: dict,
    details: dict = None,
    pricing: dict = None
) -> dict:
    """
    بيدمج البيانات من الـ 3 مصادر في dict واحد

    Args:
        graphql_course : node من GraphQL BrowseCourseSearch
        details        : response من REST /api-2.0/courses/{id}/
        pricing        : response من REST /api-2.0/pricing/

    Returns:
        dict بـ 15 عمود جاهز للـ CSV
    """

    # ══════════════════════════════════════
    # من GraphQL
    # ══════════════════════════════════════
    course_id  = graphql_course.get("id")
    title      = graphql_course.get("title", "")
    url        = graphql_course.get("urlCourseLanding", "")
    updated_on = graphql_course.get("updatedOn", "")
    is_free    = graphql_course.get("isFree", False)
    duration   = seconds_to_hours(graphql_course.get("durationInSeconds"))
    level      = graphql_course.get("level", "")
    language   = parse_language(graphql_course.get("locale"))

    # Rating
    rating_obj  = graphql_course.get("rating") or {}
    num_reviews = (
        rating_obj.get("count", 0)
        if isinstance(rating_obj, dict)
        else 0
    )

    # Instructors
    instructors      = graphql_course.get("instructors") or []
    instructor_names = ", ".join(
        i.get("name", "").strip()
        for i in instructors
        if i.get("name", "").strip()
    )

    # ══════════════════════════════════════
    # من Course Details (REST API)
    # ══════════════════════════════════════
    description     = ""
    num_subscribers = None
    type_of_course  = ""

    if details:
        description     = clean_html(details.get("description", ""))
        num_subscribers = details.get("num_subscribers")

        if details.get("instructional_level"):
            level = details["instructional_level"]

        if details.get("content_info"):
            duration = details["content_info"]

        subcategory    = details.get("primary_subcategory") or {}
        type_of_course = subcategory.get("title", "")

    skills = parse_skills(graphql_course, details)

    # ══════════════════════════════════════
    #  Pricing (REST API)
    # ══════════════════════════════════════
    price = "Free" if is_free else ""
    if pricing:
        price_obj = pricing.get("price") or {}
        price     = price_obj.get("price_string", price)

    # ══════════════════════════════════════
    #  Row 
    # ══════════════════════════════════════
    return {
        "course_id":               course_id,
        "Course_Title":            title,
        "Course_URL":              url,
        "Platform":                "Udemy",
        "Language":                language,
        "Description":             description,
        "Skills":                  skills,
        "Level":                   level,
        "Price":                   price,
        "No_of_Reviews":           num_reviews,
        "No_of_Students_enrolled": num_subscribers,
        "Programming_Instructor":  instructor_names,
        "Last_Update":             updated_on,
        "Type_of_Course":          type_of_course,
        "Duration":                duration,
    }