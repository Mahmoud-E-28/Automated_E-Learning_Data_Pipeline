# 📘 The Ultimate Course Data Pipeline: A Beginner's Guide

Welcome! This guide is written specifically for users who may not have a technical background but want to understand what this project does, why it’s so important, and how to use it effortlessly.

---

## 🌟 What is this project?

Imagine you are trying to find the perfect online course. You go to **Coursera**, **Udemy**, and **Udacity**. 
* Udemy might list a course as "Level 1" taking "300 minutes".
* Coursera might list a similar course as "Beginner" taking "5 hours".
* Udacity might use completely different tags and price formats.

If you are trying to build an app that recommends the best course to a student, this messy, mismatched data is a nightmare! 

**This project acts as a Universal Translator and Cleaner.** It takes all that messy data from different websites and magically cleans, organizes, and standardizes it into one beautiful, easy-to-read format. 

---

## 🧠 Why is this so important? (The Recommendation System)

You might have heard the phrase: *"Garbage In, Garbage Out."* 
Artificial Intelligence and Recommendation Systems are only as smart as the data you feed them. 

If we feed a recommendation system messy data, it won't realize that a Coursera course and a Udemy course are actually the perfect match for the same student. By running this pipeline first, we ensure that:
1. **Apples are compared to Apples:** Prices, difficulties, and durations are all converted into standard terms.
2. **History is remembered:** If a course changes its price or title, our system remembers the old version just in case a student liked the original syllabus.
3. **High Quality:** The pipeline automatically checks the data for missing links, broken IDs, and weird values before it ever reaches the recommendation engine.

Simply put: **This pipeline is the brain that makes the recommendation engine smart.**

---

## ⚙️ What does the pipeline actually do? (In plain English)

When you press the "Start" button, the system automatically does the following:

1. **The Cleanup Crew:** It looks at all the raw data and throws away duplicates or broken records.
2. **The Translator:** It converts varying descriptions (like "300 mins" vs "5 hours") into a single standardized format.
3. **The Organizer:** It splits the huge wall of data into neat, organized folders (one for Instructors, one for Platforms, one for the Course details).
4. **The Quality Inspector:** It runs over 70 automated checks to guarantee the data is 100% perfect.

---

## 🚀 How to use the Application

You don't need to be a programmer to run this! Just follow these simple steps to start the pipeline.

### Step 1: Start the Engine
1. Open your computer's terminal (or command prompt).
2. Navigate to the folder where you saved this project.
3. Type the following command and press Enter:
   ```bash
   docker compose up -d
   ```
   *(This tells your computer to safely turn on all the background engines).*

### Step 2: Open the Control Panel
1. Open your web browser (Chrome, Safari, Edge, etc.).
2. Go to this address: **[http://localhost:8080](http://localhost:8080)**
3. You will see a login screen. 
   * **Username:** `airflow`
   * **Password:** `airflow`

### Step 3: Run the Pipeline
You are now inside the control panel (called Apache Airflow). 
1. Look for the pipeline named **`course_data_pipeline`**.
2. On the left side of its name, you will see a little toggle switch. Click it so it turns blue (this "unpauses" the pipeline).
3. On the right side, click the **Play button** (▶️) and select **"Trigger DAG"**.

### Step 4: Watch it Work!
That's it! The system is now doing all the heavy lifting. 
* You will see little circles next to the pipeline. 
* **Light Green** means it's working.
* **Dark Green** means it finished successfully!
* *(Note: If it turns **Red**, don't panic! This usually just means the initial raw data hasn't been added to the system yet).*

### Step 5: Shutting Down
When you are completely finished and want to turn off the engine to save computer memory, go back to your terminal and type:
```bash
docker compose down -v
```

---
*Thank you for using the Course Data Pipeline! Your data is now perfectly clean and ready for the future.*
