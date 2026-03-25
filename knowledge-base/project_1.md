# Project: Amazon Review Quality Ranking System

## Executive Summary
This project addresses the **Cold Start problem** in e-commerce user reviews. Traditional ranking systems rely heavily on historical **"Helpful" votes**, which creates a **rich-get-richer feedback loop** that pushes new but high-quality reviews to the bottom of the page.

To solve this, I developed a **content-based ranking engine** that predicts the quality of a review immediately upon submission, independent of user votes.

**Core Achievement:**  
Successfully identified **"Hidden Gem" reviews** (high-value feedback with zero votes) and promoted them to top positions in ranking simulations.

**Key Innovation:**  
Defined a **Valuable Review Score (VRS)** that estimates review helpfulness using only linguistic and structural text features.

---

# 1. The Business Problem

E-commerce platforms lose valuable insights when meaningful feedback is hidden beneath emotional or popularity-driven rankings.

### Key Issues

**Cold Start Problem**
- Newly posted reviews have **no votes**, so they rarely appear near the top of rankings.

**Negative Feedback Noise**
- Constructive product criticism is often buried under emotional 1-star reviews with little useful information.

### Objective

Build an automated scoring system that surfaces **constructive, high-information reviews** for:

- Customers making purchase decisions
- Product Managers looking for actionable product feedback

---

# 2. Technical Approach & Data Pipeline

## Dataset & Target Variable

**Dataset**
- 568,000 Amazon Food Reviews

**Target Metric**
- **Wilson Lower Bound Score**

This metric was chosen instead of a simple helpfulness ratio because it accounts for statistical uncertainty in low-vote situations.

Example:

- A review with **100 helpful votes out of 100** should rank higher than
- A review with **1 helpful vote out of 1**

The **Wilson Lower Bound** provides a statistically robust ranking signal.

---

## NLP Feature Engineering

Features were designed around three dimensions of review quality.

### 1. Readability

Measures how detailed and informative a review is.

Features:
- Word count
- Unique word ratio (vocabulary richness)

---

### 2. Sentiment & Tone

Detects emotional or exaggerated writing styles that often correlate with lower review usefulness.

Features:
- Capitalization ratio (detects **"shouting" text**)
- Exclamation mark density

---

### 3. Trust & Validity

Identifies suspicious or low-quality review patterns.

Features:
- Duplicate review detection
- Template similarity checks
- Spam-like phrase patterns

---

## Modeling

**Algorithm:**  
Ridge Regression (**L2 Regularization**)

**Why Ridge Regression**

- Provides strong **interpretability**
- Handles correlated NLP features effectively
- Allows analysis of feature influence on review helpfulness

Example insight:

- High **capitalization ratios** correlate negatively with review quality.

---

## Model Evaluation

The model was trained and evaluated through several iterations.

Final performance on test data:

| Metric | Value |
|------|------|
| RMSE | 0.1975 |
| R² | 0.0382 |

Although the predictive signal is modest, the model effectively identifies **high-value review patterns** that popularity-based systems miss.

---

# 3. Results & Business Impact

## Ranking Simulation

A ranking simulation was performed on a product page:

**Product Example:**  
Oatmeal Cookies (Item ID: B007JFMH8M)

### Legacy Ranking System

Top results contained:

- Short emotional comments
- Reviews with many historical votes but limited useful information

Example:
> "I love these cookies!"

---

### VRS Ranking System

The model surfaced reviews that:

- Had **zero votes**
- Contained **detailed product insights**

Example:

A review providing a **price-per-box mathematical breakdown**, offering real decision value to buyers.

This demonstrates the model's ability to **solve the Cold Start problem**.

---

## "Calm Killer" Detection

The VRS system was also applied to **negative reviews (1–2 stars)**.

It successfully identified a specific class of reviews called **"Calm Killers."**

These reviews:

- Are polite and objective
- Provide **specific defect descriptions**
- Avoid emotional exaggeration

Examples include:

- Loose battery latch issues
- Unsealed packaging
- Manufacturing defects

These reviews provide **high-value product intelligence** for businesses.

---

# 4. Repository Structure

The project is implemented as a modular **Python pipeline**.
