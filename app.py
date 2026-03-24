import streamlit as st
import pandas as pd
import random

st.set_page_config(layout="wide")

# -----------------------------
# TIMESLOTS
# -----------------------------
timeslots = [
    "Mon-9", "Mon-11", "Mon-1",
    "Tue-9", "Tue-11", "Tue-1",
    "Wed-9", "Wed-11", "Wed-1",
    "Thu-9", "Thu-11", "Thu-1"
]

# -----------------------------
# LOAD DATA
# -----------------------------
def load_data(course_file, room_file):
    courses = pd.read_csv(course_file).to_dict(orient="records")
    rooms = pd.read_csv(room_file).to_dict(orient="records")
    return courses, rooms


# -----------------------------
# CREATE CHROMOSOME
# -----------------------------
def create_chromosome(courses, rooms):
    chromosome = []

    for c in courses:
        preferred = c.get("preferred_times", "")
        preferred_list = preferred.split("|") if isinstance(preferred, str) else []

        gene = {
            "course": c["id"],
            "room": random.choice(rooms)["id"],
            "timeslot": random.choice(timeslots),
            "lecturer": c["lecturer"],
            "department": c["department"],
            "level": c["level"],
            "preferred_times": preferred_list,
            "students": c["students"]
        }

        chromosome.append(gene)

    return chromosome


def create_population(courses, rooms, size):
    return [create_chromosome(courses, rooms) for _ in range(size)]


# -----------------------------
# FITNESS FUNCTION
# -----------------------------
def fitness(chromosome, rooms):
    penalty = 0

    # HARD CONSTRAINTS
    for i in range(len(chromosome)):
        for j in range(i + 1, len(chromosome)):

            c1 = chromosome[i]
            c2 = chromosome[j]

            # Room clash
            if c1["room"] == c2["room"] and c1["timeslot"] == c2["timeslot"]:
                penalty += 1000

            # Lecturer clash
            if c1["lecturer"] == c2["lecturer"] and c1["timeslot"] == c2["timeslot"]:
                penalty += 1000

            # Student clash (same dept + level)
            if (
                c1["department"] == c2["department"]
                and c1["level"] == c2["level"]
                and c1["timeslot"] == c2["timeslot"]
            ):
                penalty += 1000

    # Room capacity
    for gene in chromosome:
        room = next(r for r in rooms if r["id"] == gene["room"])
        if gene["students"] > room["capacity"]:
            penalty += 1000

    # SOFT CONSTRAINTS

    # Lecturer preferred time
    for gene in chromosome:
        if gene["preferred_times"]:
            if gene["timeslot"] not in gene["preferred_times"]:
                penalty += 20

    return -penalty


# -----------------------------
# GA OPERATIONS
# -----------------------------
def select(population, rooms):
    a, b = random.choice(population), random.choice(population)
    return a if fitness(a, rooms) > fitness(b, rooms) else b


def crossover(p1, p2):
    point = random.randint(1, len(p1) - 1)
    return p1[:point] + p2[point:]


def mutate(chromosome, rooms, rate=0.1):
    for gene in chromosome:
        if random.random() < rate:
            gene["room"] = random.choice(rooms)["id"]
            gene["timeslot"] = random.choice(timeslots)


def run_ga(courses, rooms, generations, pop_size):
    population = create_population(courses, rooms, pop_size)

    progress = st.progress(0)

    for gen in range(generations):
        population = sorted(population, key=lambda x: fitness(x, rooms), reverse=True)

        progress.progress((gen + 1) / generations)

        new_population = population[:5]

        while len(new_population) < pop_size:
            p1 = select(population, rooms)
            p2 = select(population, rooms)

            child = crossover(p1, p2)
            mutate(child, rooms)

            new_population.append(child)

        population = new_population

    return population[0]


# -----------------------------
# STREAMLIT UI
# -----------------------------
st.title("📅 Advanced Timetable Generator (Genetic Algorithm)")

st.sidebar.header("Upload CSV Files")

course_file = st.sidebar.file_uploader("Upload Courses CSV")
room_file = st.sidebar.file_uploader("Upload Rooms CSV")

st.sidebar.markdown("### GA Settings")
generations = st.sidebar.slider("Generations", 50, 500, 200)
pop_size = st.sidebar.slider("Population Size", 10, 100, 50)

if course_file and room_file:
    courses, rooms = load_data(course_file, room_file)

    st.success("Data Loaded Successfully")

    st.subheader("Courses")
    st.dataframe(pd.DataFrame(courses))

    st.subheader("Rooms")
    st.dataframe(pd.DataFrame(rooms))

    if st.button("🚀 Generate Timetable"):
        best = run_ga(courses, rooms, generations, pop_size)

        df = pd.DataFrame(best)

        st.success("Timetable Generated!")

        # RAW
        st.subheader("📋 Raw Timetable")
        st.dataframe(df)

        # STRUCTURED
        st.subheader("📊 Structured Timetable (Room vs Time)")
        structured = df.pivot_table(
            index="timeslot",
            columns="room",
            values="course",
            aggfunc="first"
        )
        st.dataframe(structured)

        # DOWNLOAD
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "timetable.csv")
