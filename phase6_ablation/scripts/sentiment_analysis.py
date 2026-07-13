"""
Reflection Content Sentiment Analysis
Analyzes the emotional tone and quality of self-reflection content
"""

import sqlite3
from pathlib import Path
from textblob import TextBlob
import re
from collections import Counter

DB_PATH = Path(__file__).parent / "results.db"

def analyze_sentiment(text):
    """Analyze sentiment using TextBlob"""
    blob = TextBlob(text)
    return {
        'polarity': blob.polarity,      # -1 (negative) to 1 (positive)
        'subjectivity': blob.subjectivity  # 0 (objective) to 1 (subjective)
    }

def count_patterns(text):
    """Count specific linguistic patterns"""
    patterns = {
        'self_blame': len(re.findall(r'\b(I failed|my mistake|I misunderstood|I assumed|my error)\b', text, re.I)),
        'confidence': len(re.findall(r'\b(I will|I should|I must|I need to|next time)\b', text, re.I)),
        'uncertainty': len(re.findall(r'\b(maybe|perhaps|might|possibly|could be)\b', text, re.I)),
        'concrete_actions': len(re.findall(r'kubectl|docker|bash|command|run|execute', text, re.I)),
        'verification': len(re.findall(r'\b(verify|check|confirm|validate|test)\b', text, re.I)),
        'learning': len(re.findall(r'\b(learn|lesson|insight|realize|understand)\b', text, re.I)),
        'excuses': len(re.findall(r'\b(but|however|although|unfortunately)\b', text, re.I)),
    }
    return patterns

def analyze_structure(text):
    """Analyze structural quality of reflection"""
    return {
        'has_headers': bool(re.search(r'^#+\s', text, re.M)),
        'has_bold': '**' in text,
        'has_code_blocks': '```' in text or '`' in text,
        'has_numbered_list': bool(re.search(r'^\d+\.', text, re.M)),
        'word_count': len(text.split()),
        'sentence_count': len(re.findall(r'[.!?]+', text)),
    }

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = """
    SELECT
        e.model,
        e.case_id,
        e.success,
        t.reflection_content
    FROM experiments e
    JOIN trials t ON e.id = t.experiment_id
    WHERE t.reflection_content IS NOT NULL
      AND t.reflection_content != ''
    """

    results = conn.execute(query).fetchall()

    # Aggregate by model and success
    model_stats = {}

    for row in results:
        model = row['model']
        success = row['success']
        content = row['reflection_content']

        key = (model, success)
        if key not in model_stats:
            model_stats[key] = {
                'count': 0,
                'polarity_sum': 0,
                'subjectivity_sum': 0,
                'patterns': Counter(),
                'structure': Counter(),
                'word_count_sum': 0,
            }

        stats = model_stats[key]
        stats['count'] += 1

        # Sentiment
        sentiment = analyze_sentiment(content)
        stats['polarity_sum'] += sentiment['polarity']
        stats['subjectivity_sum'] += sentiment['subjectivity']

        # Patterns
        patterns = count_patterns(content)
        for k, v in patterns.items():
            stats['patterns'][k] += v

        # Structure
        structure = analyze_structure(content)
        stats['word_count_sum'] += structure['word_count']
        for k in ['has_headers', 'has_bold', 'has_code_blocks', 'has_numbered_list']:
            if structure[k]:
                stats['structure'][k] += 1

    conn.close()

    # Print results
    print("=" * 80)
    print("REFLECTION SENTIMENT ANALYSIS")
    print("=" * 80)

    print("\n## 1. SENTIMENT SCORES (Polarity: -1 negative to +1 positive)")
    print("-" * 60)
    print(f"{'Model':<12} {'Success':<10} {'Count':<8} {'Polarity':<12} {'Subjectivity':<12}")
    print("-" * 60)

    for (model, success), stats in sorted(model_stats.items()):
        avg_pol = stats['polarity_sum'] / stats['count']
        avg_sub = stats['subjectivity_sum'] / stats['count']
        success_str = "Yes" if success else "No"
        print(f"{model:<12} {success_str:<10} {stats['count']:<8} {avg_pol:+.3f}       {avg_sub:.3f}")

    print("\n## 2. LINGUISTIC PATTERNS (Average per reflection)")
    print("-" * 80)
    pattern_names = ['self_blame', 'confidence', 'uncertainty', 'concrete_actions', 'verification', 'learning', 'excuses']
    print(f"{'Model':<10} {'Succ':<6}", end="")
    for p in pattern_names:
        print(f"{p[:8]:<10}", end="")
    print()
    print("-" * 80)

    for (model, success), stats in sorted(model_stats.items()):
        success_str = "Y" if success else "N"
        print(f"{model:<10} {success_str:<6}", end="")
        for p in pattern_names:
            avg = stats['patterns'][p] / stats['count']
            print(f"{avg:<10.1f}", end="")
        print()

    print("\n## 3. STRUCTURAL QUALITY (% of reflections with feature)")
    print("-" * 70)
    print(f"{'Model':<12} {'Success':<10} {'Headers':<10} {'Bold':<10} {'Code':<10} {'Lists':<10} {'Avg Words':<10}")
    print("-" * 70)

    for (model, success), stats in sorted(model_stats.items()):
        success_str = "Yes" if success else "No"
        headers_pct = 100 * stats['structure']['has_headers'] / stats['count']
        bold_pct = 100 * stats['structure']['has_bold'] / stats['count']
        code_pct = 100 * stats['structure']['has_code_blocks'] / stats['count']
        list_pct = 100 * stats['structure']['has_numbered_list'] / stats['count']
        avg_words = stats['word_count_sum'] / stats['count']
        print(f"{model:<12} {success_str:<10} {headers_pct:<10.0f} {bold_pct:<10.0f} {code_pct:<10.0f} {list_pct:<10.0f} {avg_words:<10.0f}")

    print("\n## 4. KEY INSIGHTS")
    print("-" * 60)

    # Compare models
    for model in ['haiku30', 'haiku35', 'haiku45']:
        fail_key = (model, 0)
        succ_key = (model, 1)

        if fail_key in model_stats and succ_key in model_stats:
            fail_pol = model_stats[fail_key]['polarity_sum'] / model_stats[fail_key]['count']
            succ_pol = model_stats[succ_key]['polarity_sum'] / model_stats[succ_key]['count']

            fail_verify = model_stats[fail_key]['patterns']['verification'] / model_stats[fail_key]['count']
            succ_verify = model_stats[succ_key]['patterns']['verification'] / model_stats[succ_key]['count']

            print(f"\n{model.upper()}:")
            print(f"  Polarity shift (fail->success): {fail_pol:+.3f} -> {succ_pol:+.3f}")
            print(f"  Verification mentions (fail->success): {fail_verify:.1f} -> {succ_verify:.1f}")

if __name__ == "__main__":
    main()
