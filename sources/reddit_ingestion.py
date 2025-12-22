"""
Reddit Data Ingestion for Peptide AI

Scrapes and processes peptide-related discussions from Reddit:
- r/peptides
- r/Nootropics
- r/steroids (peptide discussions)
- r/StackAdvice

Extracts:
- User experiences and results
- Protocol discussions
- Side effect reports
- Before/after reports
"""

import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import re
import json

logger = logging.getLogger(__name__)


@dataclass
class RedditPost:
    """Represents a Reddit post or comment"""
    id: str
    subreddit: str
    title: str
    content: str
    author: str
    score: int
    created_utc: datetime
    url: str
    post_type: str  # 'post' or 'comment'
    peptides_mentioned: List[str]
    is_experience_report: bool
    sentiment: Optional[str] = None


class RedditIngestion:
    """
    Ingests peptide-related content from Reddit using the public JSON API
    """

    # Subreddits to monitor
    SUBREDDITS = [
        'peptides',
        'Nootropics',
        'steroids',
        'StackAdvice',
        'Semaglutide',
        'tirzepatidehelp',
    ]

    # Peptide patterns to detect
    PEPTIDE_PATTERNS = [
        r'\bBPC[-\s]?157\b',
        r'\bTB[-\s]?500\b',
        r'\bthymosin\s*(alpha|beta)[-\s]?\d*\b',
        r'\bsemaglutide\b',
        r'\btirzepatide\b',
        r'\bozempic\b',
        r'\bmounjaro\b',
        r'\bGHK[-\s]?Cu\b',
        r'\bipamorelin\b',
        r'\bCJC[-\s]?1295\b',
        r'\bGHRP[-\s]?\d\b',
        r'\bmelanotan\b',
        r'\bMT[-\s]?2\b',
        r'\bPT[-\s]?141\b',
        r'\bepitalon\b',
        r'\bsemax\b',
        r'\bselank\b',
        r'\bdihexa\b',
        r'\bLL[-\s]?37\b',
        r'\bAOD[-\s]?9604\b',
        r'\btesamorelin\b',
        r'\bsermorelin\b',
        r'\bMOTS[-\s]?c\b',
        r'\bSS[-\s]?31\b',
    ]

    # Experience report indicators
    EXPERIENCE_INDICATORS = [
        r'\bmy experience\b',
        r'\bweek \d+\b',
        r'\bday \d+\b',
        r'\bmonth \d+\b',
        r'\bresults\b',
        r'\bupdate\b',
        r'\bbefore\s*(/|and)\s*after\b',
        r'\bfinished\s*(my)?\s*cycle\b',
        r'\bstarted\b.*\bago\b',
        r'\bI\'ve been (taking|using|on)\b',
        r'\bside effects?\b',
        r'\bno side effects?\b',
        r'\bnoticed\b',
        r'\bfeeling\b',
    ]

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                'User-Agent': 'PeptideAI Research Bot 1.0 (Educational Research)'
            },
            timeout=30.0
        )

    async def fetch_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 100,
        time_filter: str = 'month',  # hour, day, week, month, year, all
        sort: str = 'top'  # hot, new, top, rising
    ) -> List[Dict[str, Any]]:
        """Fetch posts from a subreddit"""
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
        params = {
            'limit': min(limit, 100),
            't': time_filter,
            'raw_json': 1,
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            posts = []
            for child in data.get('data', {}).get('children', []):
                post_data = child.get('data', {})
                posts.append(post_data)

            logger.info(f"Fetched {len(posts)} posts from r/{subreddit}")
            return posts

        except Exception as e:
            logger.error(f"Error fetching r/{subreddit}: {e}")
            return []

    async def fetch_post_comments(
        self,
        subreddit: str,
        post_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch comments for a specific post"""
        url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        params = {
            'limit': limit,
            'raw_json': 1,
            'sort': 'top',
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            comments = []
            if len(data) > 1:
                self._extract_comments(data[1].get('data', {}).get('children', []), comments)

            return comments

        except Exception as e:
            logger.error(f"Error fetching comments for {post_id}: {e}")
            return []

    def _extract_comments(self, children: List[Dict], comments: List[Dict], depth: int = 0):
        """Recursively extract comments"""
        if depth > 3:  # Limit depth
            return

        for child in children:
            if child.get('kind') != 't1':
                continue

            data = child.get('data', {})
            if data.get('body') and data.get('score', 0) >= 2:  # Filter low-quality
                comments.append(data)

            # Process replies
            replies = data.get('replies')
            if isinstance(replies, dict):
                reply_children = replies.get('data', {}).get('children', [])
                self._extract_comments(reply_children, comments, depth + 1)

    def detect_peptides(self, text: str) -> List[str]:
        """Detect peptide mentions in text"""
        found = set()
        text_lower = text.lower()

        for pattern in self.PEPTIDE_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                # Normalize the peptide name
                normalized = self._normalize_peptide(match if isinstance(match, str) else match[0] if match else '')
                if normalized:
                    found.add(normalized)

        return list(found)

    def _normalize_peptide(self, name: str) -> str:
        """Normalize peptide name to canonical form"""
        name = name.lower().strip()

        mappings = {
            'bpc 157': 'BPC-157', 'bpc-157': 'BPC-157', 'bpc157': 'BPC-157',
            'tb 500': 'TB-500', 'tb-500': 'TB-500', 'tb500': 'TB-500',
            'thymosin alpha': 'Thymosin Alpha-1', 'thymosin alpha 1': 'Thymosin Alpha-1',
            'thymosin beta': 'TB-500', 'thymosin beta 4': 'TB-500',
            'semaglutide': 'Semaglutide', 'ozempic': 'Semaglutide',
            'tirzepatide': 'Tirzepatide', 'mounjaro': 'Tirzepatide',
            'ghk cu': 'GHK-Cu', 'ghk-cu': 'GHK-Cu',
            'ipamorelin': 'Ipamorelin',
            'cjc 1295': 'CJC-1295', 'cjc-1295': 'CJC-1295',
            'ghrp 2': 'GHRP-2', 'ghrp-2': 'GHRP-2', 'ghrp 6': 'GHRP-6', 'ghrp-6': 'GHRP-6',
            'melanotan': 'Melanotan II', 'mt 2': 'Melanotan II', 'mt-2': 'Melanotan II',
            'pt 141': 'PT-141', 'pt-141': 'PT-141',
            'epitalon': 'Epitalon',
            'semax': 'Semax',
            'selank': 'Selank',
            'dihexa': 'Dihexa',
            'll 37': 'LL-37', 'll-37': 'LL-37',
            'aod 9604': 'AOD-9604', 'aod-9604': 'AOD-9604',
            'tesamorelin': 'Tesamorelin',
            'sermorelin': 'Sermorelin',
            'mots c': 'MOTS-c', 'mots-c': 'MOTS-c',
            'ss 31': 'SS-31', 'ss-31': 'SS-31',
        }

        for key, value in mappings.items():
            if key in name:
                return value

        return ''

    def is_experience_report(self, text: str) -> bool:
        """Check if text appears to be an experience report"""
        text_lower = text.lower()

        matches = 0
        for pattern in self.EXPERIENCE_INDICATORS:
            if re.search(pattern, text_lower):
                matches += 1

        # Need at least 2 indicators
        return matches >= 2

    def process_post(self, post_data: Dict[str, Any], subreddit: str) -> Optional[RedditPost]:
        """Process a raw Reddit post into structured data"""
        title = post_data.get('title', '')
        selftext = post_data.get('selftext', '')
        full_text = f"{title}\n\n{selftext}"

        # Detect peptides
        peptides = self.detect_peptides(full_text)

        # Skip if no peptides mentioned
        if not peptides:
            return None

        # Check if experience report
        is_experience = self.is_experience_report(full_text)

        return RedditPost(
            id=post_data.get('id', ''),
            subreddit=subreddit,
            title=title,
            content=selftext,
            author=post_data.get('author', '[deleted]'),
            score=post_data.get('score', 0),
            created_utc=datetime.fromtimestamp(post_data.get('created_utc', 0)),
            url=f"https://reddit.com{post_data.get('permalink', '')}",
            post_type='post',
            peptides_mentioned=peptides,
            is_experience_report=is_experience,
        )

    def process_comment(self, comment_data: Dict[str, Any], subreddit: str) -> Optional[RedditPost]:
        """Process a raw Reddit comment into structured data"""
        body = comment_data.get('body', '')

        if not body or body == '[deleted]' or body == '[removed]':
            return None

        # Detect peptides
        peptides = self.detect_peptides(body)

        # Skip if no peptides mentioned
        if not peptides:
            return None

        # Check if experience report
        is_experience = self.is_experience_report(body)

        return RedditPost(
            id=comment_data.get('id', ''),
            subreddit=subreddit,
            title='',
            content=body,
            author=comment_data.get('author', '[deleted]'),
            score=comment_data.get('score', 0),
            created_utc=datetime.fromtimestamp(comment_data.get('created_utc', 0)),
            url=f"https://reddit.com{comment_data.get('permalink', '')}",
            post_type='comment',
            peptides_mentioned=peptides,
            is_experience_report=is_experience,
        )

    async def search_peptide(self, peptide: str, limit: int = 50) -> List[RedditPost]:
        """Search Reddit for posts about a specific peptide"""
        results = []

        for subreddit in self.SUBREDDITS:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {
                'q': peptide,
                'restrict_sr': 1,
                'limit': limit,
                'sort': 'relevance',
                't': 'year',
                'raw_json': 1,
            }

            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                for child in data.get('data', {}).get('children', []):
                    post = self.process_post(child.get('data', {}), subreddit)
                    if post:
                        results.append(post)

            except Exception as e:
                logger.error(f"Error searching {peptide} in r/{subreddit}: {e}")

        return results

    async def ingest_all(self, posts_per_sub: int = 100) -> List[RedditPost]:
        """Ingest posts from all monitored subreddits"""
        all_posts = []

        for subreddit in self.SUBREDDITS:
            logger.info(f"Ingesting r/{subreddit}...")

            # Fetch top posts
            raw_posts = await self.fetch_subreddit_posts(
                subreddit,
                limit=posts_per_sub,
                time_filter='month',
                sort='top'
            )

            for raw_post in raw_posts:
                post = self.process_post(raw_post, subreddit)
                if post:
                    all_posts.append(post)

                    # Fetch comments for experience reports
                    if post.is_experience_report and post.score >= 10:
                        comments = await self.fetch_post_comments(subreddit, post.id)
                        for raw_comment in comments:
                            comment = self.process_comment(raw_comment, subreddit)
                            if comment:
                                all_posts.append(comment)

            # Rate limiting
            await asyncio.sleep(1)

        logger.info(f"Total posts ingested: {len(all_posts)}")
        logger.info(f"Experience reports: {sum(1 for p in all_posts if p.is_experience_report)}")

        return all_posts

    def to_weaviate_format(self, post: RedditPost) -> Dict[str, Any]:
        """Convert RedditPost to Weaviate document format"""
        return {
            'title': post.title if post.title else f"Reddit comment about {', '.join(post.peptides_mentioned)}",
            'content': post.content,
            'source_type': 'reddit',
            'url': post.url,
            'citation': f"Reddit r/{post.subreddit} - u/{post.author} ({post.created_utc.strftime('%Y-%m-%d')})",
            'peptides': post.peptides_mentioned,
            'metadata': {
                'subreddit': post.subreddit,
                'author': post.author,
                'score': post.score,
                'post_type': post.post_type,
                'is_experience_report': post.is_experience_report,
            }
        }

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


async def run_reddit_ingestion():
    """Run the Reddit ingestion pipeline"""
    ingestion = RedditIngestion()

    try:
        posts = await ingestion.ingest_all(posts_per_sub=50)

        # Convert to Weaviate format
        documents = [ingestion.to_weaviate_format(p) for p in posts]

        # Save to file for inspection
        with open('reddit_data.json', 'w') as f:
            json.dump(documents, f, indent=2, default=str)

        logger.info(f"Saved {len(documents)} documents to reddit_data.json")

        return documents

    finally:
        await ingestion.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_reddit_ingestion())
