import praw
from collections import defaultdict
import re
import datetime
import configparser
import os
from typing import List, Dict, Tuple

class RedditPersonaGenerator:
    def __init__(self):
        # Load configuration from praw.ini
        self.config = configparser.ConfigParser()
        self.config.read('praw.ini')
        
        # Initialize Reddit instance
        self.reddit = praw.Reddit(
            client_id=self.config['REDDIT']['client_id'],
            client_secret=self.config['REDDIT']['client_secret'],
            user_agent=self.config['REDDIT']['user_agent']
        )
        
    def extract_user_info(self, username: str) -> Dict:
        """Extract user information and activity from Reddit"""
        user = self.reddit.redditor(username)
        
        try:
            # Basic user info
            user_info = {
                'username': username,
                'created_utc': datetime.datetime.fromtimestamp(user.created_utc).strftime('%Y-%m-%d'),
                'comment_karma': user.comment_karma,
                'link_karma': user.link_karma,
                'is_mod': user.is_mod,
                'is_gold': user.is_gold,
                'comments': [],
                'posts': []
            }
            
            # Get recent comments (limit to 100 for practicality)
            for comment in user.comments.new(limit=100):
                user_info['comments'].append({
                    'body': comment.body,
                    'subreddit': str(comment.subreddit),
                    'created_utc': datetime.datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d'),
                    'score': comment.score,
                    'permalink': f"https://reddit.com{comment.permalink}"
                })
            
            # Get recent posts (limit to 50)
            for submission in user.submissions.new(limit=50):
                user_info['posts'].append({
                    'title': submission.title,
                    'selftext': submission.selftext,
                    'subreddit': str(submission.subreddit),
                    'created_utc': datetime.datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d'),
                    'score': submission.score,
                    'permalink': f"https://reddit.com{submission.permalink}",
                    'is_self': submission.is_self,
                    'url': submission.url
                })
                
            return user_info
            
        except Exception as e:
            print(f"Error fetching user data: {e}")
            return None
    
    def analyze_persona(self, user_info: Dict) -> Dict:
        """Analyze user data to build a persona"""
        persona = {
            'basic_info': {
                'Username': user_info['username'],
                'Account Age': self._calculate_account_age(user_info['created_utc']),
                'Comment Karma': user_info['comment_karma'],
                'Post Karma': user_info['link_karma'],
                'Premium Member': user_info['is_gold']
            },
            'interests': defaultdict(list),
            'personality_traits': defaultdict(list),
            'frequent_subreddits': defaultdict(int),
            'activity_patterns': defaultdict(int),
            'language_style': defaultdict(int)
        }
        
        # Analyze comments
        for comment in user_info['comments']:
            self._analyze_comment(comment, persona)
            persona['frequent_subreddits'][comment['subreddit']] += 1
            self._analyze_activity_time(comment['created_utc'], persona)
            
        # Analyze posts
        for post in user_info['posts']:
            self._analyze_post(post, persona)
            persona['frequent_subreddits'][post['subreddit']] += 1
            self._analyze_activity_time(post['created_utc'], persona)
            
        # Process findings
        persona['top_interests'] = sorted(
            persona['interests'].items(), 
            key=lambda x: len(x[1]), 
            reverse=True
        )[:5]
        
        persona['top_subreddits'] = sorted(
            persona['frequent_subreddits'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return persona
    
    def _calculate_account_age(self, created_date: str) -> str:
        """Calculate account age in years/months"""
        created = datetime.datetime.strptime(created_date, '%Y-%m-%d')
        delta = datetime.datetime.now() - created
        years = delta.days // 365
        months = (delta.days % 365) // 30
        return f"{years} years, {months} months"
    
    def _analyze_comment(self, comment: Dict, persona: Dict):
        """Analyze a single comment for persona traits"""
        text = comment['body'].lower()
        
        # Detect interests
        if any(tech in text for tech in ['python', 'javascript', 'java', 'c++']):
            persona['interests']['programming'].append(comment['permalink'])
        if any(word in text for word in ['game', 'gaming', 'playstation', 'xbox']):
            persona['interests']['gaming'].append(comment['permalink'])
        if any(word in text for word in ['movie', 'film', 'netflix', 'hbo']):
            persona['interests']['movies'].append(comment['permalink'])
        
        # Detect personality traits
        if any(word in text for word in ['i think', 'in my opinion']):
            persona['personality_traits']['opinionated'].append(comment['permalink'])
        if '?' in text:
            persona['personality_traits']['inquisitive'].append(comment['permalink'])
        if any(word in text for word in ['thanks', 'thank you', 'appreciate']):
            persona['personality_traits']['polite'].append(comment['permalink'])
            
        # Analyze language style
        persona['language_style']['comment_length'] += len(text.split())
        if '!' in text:
            persona['language_style']['exclamation_use'] += 1
        if re.search(r'\b(i\'m|i am|me|my)\b', text):
            persona['language_style']['self_reference'] += 1
    
    def _analyze_post(self, post: Dict, persona: Dict):
        """Analyze a single post for persona traits"""
        text = (post['title'] + ' ' + post.get('selftext', '')).lower()
        
        # Detect interests from posts
        if any(word in text for word in ['help', 'advice', 'suggestion']):
            persona['interests']['help_seeking'].append(post['permalink'])
        if any(word in text for word in ['discussion', 'debate', 'opinion']):
            persona['interests']['discussions'].append(post['permalink'])
        if '?' in post['title']:
            persona['personality_traits']['inquisitive'].append(post['permalink'])
            
    def _analyze_activity_time(self, timestamp: str, persona: Dict):
        """Analyze when the user is most active"""
        dt = datetime.datetime.strptime(timestamp, '%Y-%m-%d')
        hour = dt.hour
        
        if 5 <= hour < 12:
            persona['activity_patterns']['morning'] += 1
        elif 12 <= hour < 17:
            persona['activity_patterns']['afternoon'] += 1
        elif 17 <= hour < 22:
            persona['activity_patterns']['evening'] += 1
        else:
            persona['activity_patterns']['night'] += 1
    
    def generate_persona_file(self, persona: Dict, filename: str):
        """Generate a text file with the persona analysis"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== REDDIT USER PERSONA ===\n\n")
            
            # Basic Info
            f.write("== BASIC INFORMATION ==\n")
            for key, value in persona['basic_info'].items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # Top Interests
            f.write("== TOP INTERESTS ==\n")
            for interest, citations in persona['top_interests']:
                f.write(f"- {interest.capitalize()} (based on {len(citations)} comments/posts)\n")
                for url in citations[:3]:  # Show top 3 citations
                    f.write(f"  - Citation: {url}\n")
            f.write("\n")
            
            # Personality Traits
            f.write("== PERSONALITY TRAITS ==\n")
            for trait, citations in persona['personality_traits'].items():
                f.write(f"- {trait.capitalize()} (based on {len(citations)} comments/posts)\n")
                for url in citations[:2]:  # Show top 2 citations
                    f.write(f"  - Citation: {url}\n")
            f.write("\n")
            
            # Activity Patterns
            f.write("== ACTIVITY PATTERNS ==\n")
            total_activity = sum(persona['activity_patterns'].values())
            for time, count in persona['activity_patterns'].items():
                percentage = (count / total_activity) * 100
                f.write(f"- Most active during {time}: {percentage:.1f}% of activity\n")
            f.write("\n")
            
            # Language Style
            f.write("== LANGUAGE STYLE ==\n")
            if persona['language_style']['comment_length'] > 0:
                avg_length = persona['language_style']['comment_length'] / \
                           (len(persona['personality_traits']) + len(persona['interests']))
                f.write(f"- Average comment length: {avg_length:.1f} words\n")
            if persona['language_style']['exclamation_use'] > 0:
                f.write("- Frequently uses exclamation marks\n")
            if persona['language_style']['self_reference'] > 0:
                f.write("- Often uses self-referential language (I, me, my)\n")
            f.write("\n")
            
            # Frequent Subreddits
            f.write("== FREQUENTLY VISITED SUBREDDITS ==\n")
            for subreddit, count in persona['top_subreddits']:
                f.write(f"- r/{subreddit}: {count} interactions\n")
            
            f.write("\n=== END OF PERSONA ===")

def main():
    print("Reddit User Persona Generator")
    print("-----------------------------\n")
    
    generator = RedditPersonaGenerator()
    
    # Get Reddit profile URL from user
    profile_url = input("Enter Reddit profile URL (e.g., https://www.reddit.com/user/username/): ").strip()
    username = profile_url.split('/user/')[-1].strip('/')
    
    if not username:
        print("Invalid Reddit profile URL. Please include the username.")
        return
    
    print(f"\nFetching data for user: {username}...")
    
    # Extract user info
    user_info = generator.extract_user_info(username)
    if not user_info:
        print("Failed to fetch user data. Please check the username and try again.")
        return
    
    # Analyze and generate persona
    print("Analyzing user data and generating persona...")
    persona = generator.analyze_persona(user_info)
    
    # Save to file
    filename = f"reddit_persona_{username}.txt"
    generator.generate_persona_file(persona, filename)
    
    print(f"\nPersona generated successfully! Saved to: {filename}")
    print("\nNote: Due to API limitations, this analysis is based on the user's most recent 100 comments and 50 posts.")

if __name__ == "__main__":
    main()