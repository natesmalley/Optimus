"""
Solution Search Integration
==========================

External solution search service that integrates with Stack Overflow API, 
GitHub Issues search, and other knowledge sources to find solutions for
errors that aren't in the local solution library.

Features:
- Stack Overflow API integration with intelligent query generation
- GitHub Issues and Discussions search
- Error message normalization for better search results
- Solution validation and scoring
- Automatic solution import and refinement
- Rate limiting and API quota management
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import aiohttp

from ..config import get_settings

logger = logging.getLogger("optimus.solution_search")


@dataclass
class ExternalSolution:
    """Solution found from external sources."""
    source: str  # stackoverflow, github, docs
    title: str
    description: str
    solution_text: str
    url: str
    score: float  # Relevance/quality score
    votes: int
    accepted: bool
    author: str
    created_date: datetime
    tags: List[str]
    language: Optional[str] = None
    framework: Optional[str] = None
    code_snippets: List[str] = None


@dataclass
class SearchQuery:
    """Normalized search query."""
    original_error: str
    normalized_error: str
    keywords: List[str]
    language: Optional[str]
    framework: Optional[str]
    error_type: str
    search_terms: List[str]


class SolutionSearchService:
    """
    Service for searching external sources for solutions to programming errors.
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # API Configuration
        self.stackoverflow_api_key = getattr(self.settings, 'STACKOVERFLOW_API_KEY', None)
        self.github_token = getattr(self.settings, 'GITHUB_TOKEN', None)
        
        # Rate limiting
        self.rate_limits = {
            'stackoverflow': {'requests': 0, 'reset_time': 0, 'max_per_day': 10000},
            'github': {'requests': 0, 'reset_time': 0, 'max_per_hour': 5000}
        }
        
        # Search result cache
        self.search_cache: Dict[str, List[ExternalSolution]] = {}
        self.cache_ttl = timedelta(hours=6)
        
        # HTTP session for connection pooling
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Optimus-Troubleshooting-Bot/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def search_solutions(
        self,
        error_message: str,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        max_results: int = 10
    ) -> List[ExternalSolution]:
        """
        Search for solutions across multiple external sources.
        
        Args:
            error_message: The error message to search for
            language: Programming language (optional)
            framework: Framework/library (optional)
            max_results: Maximum number of results to return
        
        Returns:
            List of external solutions ranked by relevance
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(error_message, language, framework)
            
            # Check cache first
            if cache_key in self.search_cache:
                cached_results = self.search_cache[cache_key]
                if cached_results:
                    logger.debug(f"Returning {len(cached_results)} cached search results")
                    return cached_results[:max_results]
            
            # Generate search query
            query = self._generate_search_query(error_message, language, framework)
            
            # Search multiple sources concurrently
            search_tasks = []
            
            # Stack Overflow search
            if self._can_make_request('stackoverflow'):
                search_tasks.append(self._search_stackoverflow(query))
            
            # GitHub search
            if self._can_make_request('github'):
                search_tasks.append(self._search_github(query))
            
            # Execute searches concurrently
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Combine and process results
            all_solutions = []
            for result in search_results:
                if isinstance(result, list):
                    all_solutions.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Search error: {result}")
            
            # Rank and filter solutions
            ranked_solutions = self._rank_solutions(all_solutions, query)
            
            # Cache results
            self.search_cache[cache_key] = ranked_solutions
            
            logger.info(f"Found {len(ranked_solutions)} solutions for error: {error_message[:50]}...")
            
            return ranked_solutions[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching for solutions: {e}", exc_info=True)
            return []
    
    def _generate_cache_key(self, error_message: str, language: Optional[str], framework: Optional[str]) -> str:
        """Generate cache key for search results."""
        key_data = f"{error_message}:{language}:{framework}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _generate_search_query(self, error_message: str, language: Optional[str], framework: Optional[str]) -> SearchQuery:
        """Generate optimized search query from error message."""
        
        # Normalize error message
        normalized = self._normalize_error_message(error_message)
        
        # Extract keywords
        keywords = self._extract_keywords(normalized)
        
        # Detect error type
        error_type = self._detect_error_type(error_message)
        
        # Generate search terms
        search_terms = self._generate_search_terms(normalized, keywords, language, framework)
        
        return SearchQuery(
            original_error=error_message,
            normalized_error=normalized,
            keywords=keywords,
            language=language,
            framework=framework,
            error_type=error_type,
            search_terms=search_terms
        )
    
    def _normalize_error_message(self, error_message: str) -> str:
        """Normalize error message for better search results."""
        normalized = error_message
        
        # Remove file paths and line numbers
        normalized = re.sub(r'File "([^"]+)", line \d+', 'File "[PATH]", line [LINE]', normalized)
        normalized = re.sub(r'/[^\s]+\.(py|js|java|go|rs|php|rb)', '[PATH].[EXT]', normalized)
        normalized = re.sub(r'line \d+', 'line [LINE]', normalized)
        
        # Remove specific variable names and values
        normalized = re.sub(r"'[^']*'", "'[VAR]'", normalized)
        normalized = re.sub(r'"[^"]*"', '"[VAR]"', normalized)
        normalized = re.sub(r'\b\d+\b', '[NUM]', normalized)
        
        # Remove stack trace noise
        normalized = re.sub(r'0x[a-fA-F0-9]+', '[ADDR]', normalized)
        normalized = re.sub(r'at \d+:\d+', 'at [POS]', normalized)
        
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _extract_keywords(self, error_message: str) -> List[str]:
        """Extract relevant keywords from error message."""
        keywords = []
        
        # Common error patterns and their keywords
        error_patterns = {
            r'ModuleNotFoundError': ['module', 'import', 'missing dependency'],
            r'ImportError': ['import', 'module', 'library'],
            r'SyntaxError': ['syntax', 'grammar', 'parsing'],
            r'TypeError': ['type', 'wrong type', 'casting'],
            r'AttributeError': ['attribute', 'method', 'object'],
            r'FileNotFoundError': ['file', 'path', 'missing file'],
            r'PermissionError': ['permission', 'access', 'denied'],
            r'ConnectionError': ['network', 'connection', 'timeout'],
            r'Cannot find module': ['module', 'npm', 'dependency'],
            r'command not found': ['command', 'PATH', 'installation'],
            r'Port.*already in use': ['port', 'address', 'network'],
            r'No space left on device': ['disk', 'space', 'storage'],
            r'Out[Oo]f[Mm]emory': ['memory', 'heap', 'allocation'],
        }
        
        for pattern, pattern_keywords in error_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                keywords.extend(pattern_keywords)
        
        # Extract quoted strings (often module names, commands, etc.)
        quoted_strings = re.findall(r"'([^']+)'|\"([^\"]+)\"", error_message)
        for match in quoted_strings:
            keyword = match[0] or match[1]
            if len(keyword) > 2 and not keyword.isdigit():
                keywords.append(keyword)
        
        # Remove duplicates and sort by relevance
        return list(dict.fromkeys(keywords))
    
    def _detect_error_type(self, error_message: str) -> str:
        """Detect the type of error for categorization."""
        error_types = {
            'dependency': [r'ModuleNotFoundError', r'ImportError', r'Cannot find module', r'No module named'],
            'syntax': [r'SyntaxError', r'ParseError', r'Invalid syntax'],
            'runtime': [r'TypeError', r'AttributeError', r'ValueError', r'RuntimeError'],
            'network': [r'ConnectionError', r'TimeoutError', r'refused', r'unreachable'],
            'filesystem': [r'FileNotFoundError', r'PermissionError', r'No such file'],
            'memory': [r'OutOfMemoryError', r'MemoryError', r'heap'],
            'configuration': [r'ConfigurationError', r'Invalid configuration'],
            'build': [r'Build failed', r'Compilation error', r'cannot compile']
        }
        
        for error_type, patterns in error_types.items():
            for pattern in patterns:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return error_type
        
        return 'unknown'
    
    def _generate_search_terms(self, normalized_error: str, keywords: List[str], language: Optional[str], framework: Optional[str]) -> List[str]:
        """Generate optimized search terms for external APIs."""
        terms = []
        
        # Base search with error message
        base_terms = normalized_error[:100]  # Limit length for API
        terms.append(base_terms)
        
        # Language-specific search
        if language:
            terms.append(f"{language} {base_terms}")
            
        # Framework-specific search
        if framework:
            terms.append(f"{framework} {base_terms}")
            
        # Keyword-based searches
        if keywords:
            keyword_combinations = []
            
            # Single keywords with language
            for keyword in keywords[:3]:  # Top 3 keywords
                if language:
                    keyword_combinations.append(f"{language} {keyword}")
                keyword_combinations.append(keyword)
            
            # Keyword pairs
            for i, keyword1 in enumerate(keywords[:2]):
                for keyword2 in keywords[i+1:3]:
                    keyword_combinations.append(f"{keyword1} {keyword2}")
            
            terms.extend(keyword_combinations)
        
        # Remove duplicates and empty terms
        unique_terms = []
        for term in terms:
            clean_term = ' '.join(term.split())  # Clean whitespace
            if clean_term and clean_term not in unique_terms:
                unique_terms.append(clean_term)
        
        return unique_terms[:5]  # Limit to top 5 search terms
    
    async def _search_stackoverflow(self, query: SearchQuery) -> List[ExternalSolution]:
        """Search Stack Overflow using the API."""
        if not self.session:
            return []
            
        solutions = []
        
        try:
            for search_term in query.search_terms[:3]:  # Limit API calls
                url = "https://api.stackexchange.com/2.3/search/advanced"
                
                params = {
                    'order': 'desc',
                    'sort': 'votes',
                    'q': search_term,
                    'site': 'stackoverflow',
                    'pagesize': 5,
                    'filter': 'withbody'  # Include answer bodies
                }
                
                if query.language:
                    params['tagged'] = query.language
                
                if self.stackoverflow_api_key:
                    params['key'] = self.stackoverflow_api_key
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data.get('items', []):
                            solution = self._parse_stackoverflow_result(item, query)
                            if solution:
                                solutions.append(solution)
                        
                        self._update_rate_limit('stackoverflow')
                        
                        # Respect API rate limiting
                        await asyncio.sleep(0.1)
                    
                    elif response.status == 429:  # Rate limited
                        logger.warning("Stack Overflow API rate limited")
                        break
                    else:
                        logger.warning(f"Stack Overflow API error: {response.status}")
            
        except Exception as e:
            logger.error(f"Error searching Stack Overflow: {e}")
        
        return solutions
    
    def _parse_stackoverflow_result(self, item: Dict[str, Any], query: SearchQuery) -> Optional[ExternalSolution]:
        """Parse Stack Overflow API result into ExternalSolution."""
        try:
            # Get the best answer if available
            answer_count = item.get('answer_count', 0)
            is_answered = item.get('is_answered', False)
            
            # Basic solution from question
            solution = ExternalSolution(
                source='stackoverflow',
                title=item['title'],
                description=self._extract_text_snippet(item.get('body', ''), 200),
                solution_text=item.get('body', ''),
                url=item['link'],
                score=self._calculate_relevance_score(item, query),
                votes=item.get('score', 0),
                accepted=is_answered and answer_count > 0,
                author=item.get('owner', {}).get('display_name', 'Unknown'),
                created_date=datetime.fromtimestamp(item['creation_date']),
                tags=item.get('tags', []),
                language=query.language,
                framework=query.framework,
                code_snippets=self._extract_code_snippets(item.get('body', ''))
            )
            
            return solution
            
        except Exception as e:
            logger.debug(f"Error parsing Stack Overflow result: {e}")
            return None
    
    async def _search_github(self, query: SearchQuery) -> List[ExternalSolution]:
        """Search GitHub Issues and Discussions."""
        if not self.session:
            return []
            
        solutions = []
        
        try:
            for search_term in query.search_terms[:2]:  # Limit API calls
                # Search Issues
                url = "https://api.github.com/search/issues"
                
                # Build search query
                github_query = f"{search_term} in:title,body type:issue state:closed"
                if query.language:
                    github_query += f" language:{query.language}"
                
                params = {
                    'q': github_query,
                    'sort': 'interactions',
                    'order': 'desc',
                    'per_page': 10
                }
                
                headers = {}
                if self.github_token:
                    headers['Authorization'] = f'token {self.github_token}'
                
                async with self.session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data.get('items', []):
                            solution = self._parse_github_result(item, query)
                            if solution:
                                solutions.append(solution)
                        
                        self._update_rate_limit('github')
                        
                        # Respect API rate limiting
                        await asyncio.sleep(0.1)
                    
                    elif response.status == 403:  # Rate limited
                        logger.warning("GitHub API rate limited")
                        break
                    else:
                        logger.warning(f"GitHub API error: {response.status}")
            
        except Exception as e:
            logger.error(f"Error searching GitHub: {e}")
        
        return solutions
    
    def _parse_github_result(self, item: Dict[str, Any], query: SearchQuery) -> Optional[ExternalSolution]:
        """Parse GitHub API result into ExternalSolution."""
        try:
            # Extract repository language from URL if not specified
            language = query.language
            if not language:
                repo_url = item.get('repository_url', '')
                # This would require additional API call to get repo language
                # For now, use the query language
                pass
            
            solution = ExternalSolution(
                source='github',
                title=item['title'],
                description=self._extract_text_snippet(item.get('body', ''), 200),
                solution_text=item.get('body', ''),
                url=item['html_url'],
                score=self._calculate_github_relevance_score(item, query),
                votes=item.get('reactions', {}).get('+1', 0),
                accepted=item.get('state') == 'closed',
                author=item.get('user', {}).get('login', 'Unknown'),
                created_date=datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')),
                tags=item.get('labels', []),
                language=language,
                framework=query.framework,
                code_snippets=self._extract_code_snippets(item.get('body', ''))
            )
            
            return solution
            
        except Exception as e:
            logger.debug(f"Error parsing GitHub result: {e}")
            return None
    
    def _extract_text_snippet(self, text: str, max_length: int) -> str:
        """Extract clean text snippet from HTML/Markdown content."""
        if not text:
            return ""
        
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        # Remove Markdown formatting
        clean_text = re.sub(r'[*_`#]', '', clean_text)
        
        # Remove excessive whitespace
        clean_text = ' '.join(clean_text.split())
        
        # Truncate to max length
        if len(clean_text) > max_length:
            clean_text = clean_text[:max_length] + "..."
        
        return clean_text
    
    def _extract_code_snippets(self, content: str) -> List[str]:
        """Extract code snippets from content."""
        snippets = []
        
        # Extract fenced code blocks
        fenced_pattern = r'```[^\n]*\n(.*?)```'
        fenced_matches = re.findall(fenced_pattern, content, re.DOTALL)
        snippets.extend([match.strip() for match in fenced_matches])
        
        # Extract inline code blocks
        inline_pattern = r'`([^`]+)`'
        inline_matches = re.findall(inline_pattern, content)
        snippets.extend([match.strip() for match in inline_matches if len(match.strip()) > 10])
        
        # Extract indented code blocks (basic heuristic)
        lines = content.split('\n')
        code_block = []
        in_code = False
        
        for line in lines:
            if line.startswith('    ') or line.startswith('\t'):  # Indented line
                code_block.append(line.strip())
                in_code = True
            else:
                if in_code and code_block:
                    snippet = '\n'.join(code_block)
                    if len(snippet.strip()) > 20:  # Minimum code length
                        snippets.append(snippet)
                code_block = []
                in_code = False
        
        # Add final code block if exists
        if code_block:
            snippet = '\n'.join(code_block)
            if len(snippet.strip()) > 20:
                snippets.append(snippet)
        
        return snippets[:5]  # Limit to 5 snippets
    
    def _calculate_relevance_score(self, item: Dict[str, Any], query: SearchQuery) -> float:
        """Calculate relevance score for Stack Overflow result."""
        score = 0.0
        
        # Base score from votes
        votes = item.get('score', 0)
        score += min(votes / 100, 0.3)  # Max 0.3 from votes
        
        # Boost for accepted answers
        if item.get('is_answered', False):
            score += 0.2
        
        # Boost for recent activity
        creation_date = datetime.fromtimestamp(item['creation_date'])
        days_old = (datetime.now() - creation_date).days
        if days_old < 365:  # Less than a year old
            score += 0.1
        
        # Title relevance
        title_lower = item['title'].lower()
        for keyword in query.keywords:
            if keyword.lower() in title_lower:
                score += 0.05
        
        # Tag relevance
        tags = item.get('tags', [])
        if query.language and query.language.lower() in [tag.lower() for tag in tags]:
            score += 0.1
        
        if query.framework and query.framework.lower() in [tag.lower() for tag in tags]:
            score += 0.1
        
        # View count (popularity)
        view_count = item.get('view_count', 0)
        score += min(view_count / 10000, 0.1)  # Max 0.1 from views
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_github_relevance_score(self, item: Dict[str, Any], query: SearchQuery) -> float:
        """Calculate relevance score for GitHub result."""
        score = 0.0
        
        # Base score from reactions
        reactions = item.get('reactions', {})
        positive_reactions = reactions.get('+1', 0) + reactions.get('heart', 0)
        score += min(positive_reactions / 20, 0.2)  # Max 0.2 from reactions
        
        # Boost for closed issues (likely resolved)
        if item.get('state') == 'closed':
            score += 0.3
        
        # Comment count (activity indicator)
        comments = item.get('comments', 0)
        score += min(comments / 50, 0.2)  # Max 0.2 from comments
        
        # Title relevance
        title_lower = item['title'].lower()
        for keyword in query.keywords:
            if keyword.lower() in title_lower:
                score += 0.05
        
        # Label relevance
        labels = [label.get('name', '') for label in item.get('labels', [])]
        for label in labels:
            if 'bug' in label.lower() or 'fix' in label.lower() or 'solve' in label.lower():
                score += 0.1
                break
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _rank_solutions(self, solutions: List[ExternalSolution], query: SearchQuery) -> List[ExternalSolution]:
        """Rank solutions by relevance and quality."""
        
        def calculate_final_score(solution: ExternalSolution) -> float:
            final_score = solution.score
            
            # Boost for exact keyword matches in title
            title_lower = solution.title.lower()
            keyword_matches = sum(1 for keyword in query.keywords if keyword.lower() in title_lower)
            final_score += keyword_matches * 0.05
            
            # Boost for code snippets
            if solution.code_snippets:
                final_score += min(len(solution.code_snippets) * 0.02, 0.1)
            
            # Source preference (Stack Overflow slightly preferred for code issues)
            if solution.source == 'stackoverflow':
                final_score += 0.05
            
            # Language/framework match bonus
            if query.language and solution.language == query.language:
                final_score += 0.1
            
            if query.framework and solution.framework == query.framework:
                final_score += 0.1
            
            # Recency bonus
            days_old = (datetime.now() - solution.created_date.replace(tzinfo=None)).days
            if days_old < 30:
                final_score += 0.05
            elif days_old < 365:
                final_score += 0.02
            
            return final_score
        
        # Calculate final scores and sort
        scored_solutions = [(solution, calculate_final_score(solution)) for solution in solutions]
        scored_solutions.sort(key=lambda x: x[1], reverse=True)
        
        return [solution for solution, _ in scored_solutions]
    
    def _can_make_request(self, service: str) -> bool:
        """Check if we can make a request to the service (rate limiting)."""
        if service not in self.rate_limits:
            return True
        
        limit_info = self.rate_limits[service]
        current_time = time.time()
        
        # Reset counter if time window has passed
        if current_time > limit_info['reset_time']:
            limit_info['requests'] = 0
            if service == 'stackoverflow':
                limit_info['reset_time'] = current_time + 86400  # 24 hours
            else:  # github
                limit_info['reset_time'] = current_time + 3600   # 1 hour
        
        # Check if under limit
        max_requests = limit_info.get('max_per_day' if service == 'stackoverflow' else 'max_per_hour', 1000)
        return limit_info['requests'] < max_requests
    
    def _update_rate_limit(self, service: str):
        """Update rate limit counter after making a request."""
        if service in self.rate_limits:
            self.rate_limits[service]['requests'] += 1
    
    async def get_solution_details(self, solution: ExternalSolution) -> Dict[str, Any]:
        """Get additional details for a solution (comments, answers, etc.)."""
        if not self.session:
            return {}
        
        try:
            if solution.source == 'stackoverflow':
                return await self._get_stackoverflow_details(solution)
            elif solution.source == 'github':
                return await self._get_github_details(solution)
        except Exception as e:
            logger.error(f"Error getting solution details: {e}")
        
        return {}
    
    async def _get_stackoverflow_details(self, solution: ExternalSolution) -> Dict[str, Any]:
        """Get detailed information from Stack Overflow."""
        # Extract question ID from URL
        match = re.search(r'/questions/(\d+)/', solution.url)
        if not match:
            return {}
        
        question_id = match.group(1)
        
        try:
            # Get answers for the question
            url = f"https://api.stackexchange.com/2.3/questions/{question_id}/answers"
            params = {
                'order': 'desc',
                'sort': 'votes',
                'site': 'stackoverflow',
                'filter': 'withbody',
                'pagesize': 5
            }
            
            if self.stackoverflow_api_key:
                params['key'] = self.stackoverflow_api_key
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    answers = []
                    for answer in data.get('items', []):
                        answers.append({
                            'body': answer.get('body', ''),
                            'score': answer.get('score', 0),
                            'is_accepted': answer.get('is_accepted', False),
                            'author': answer.get('owner', {}).get('display_name', 'Unknown'),
                            'code_snippets': self._extract_code_snippets(answer.get('body', ''))
                        })
                    
                    return {'answers': answers}
        
        except Exception as e:
            logger.debug(f"Error getting Stack Overflow details: {e}")
        
        return {}
    
    async def _get_github_details(self, solution: ExternalSolution) -> Dict[str, Any]:
        """Get detailed information from GitHub."""
        try:
            # Extract issue details from URL
            match = re.search(r'github\.com/([^/]+)/([^/]+)/issues/(\d+)', solution.url)
            if not match:
                return {}
            
            owner, repo, issue_number = match.groups()
            
            # Get issue comments
            url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
            
            headers = {}
            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    comments = []
                    for comment in data[:5]:  # Limit to first 5 comments
                        comments.append({
                            'body': comment.get('body', ''),
                            'author': comment.get('user', {}).get('login', 'Unknown'),
                            'created_at': comment.get('created_at', ''),
                            'code_snippets': self._extract_code_snippets(comment.get('body', ''))
                        })
                    
                    return {'comments': comments}
        
        except Exception as e:
            logger.debug(f"Error getting GitHub details: {e}")
        
        return {}
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search service statistics."""
        return {
            'cache_size': len(self.search_cache),
            'rate_limits': self.rate_limits.copy(),
            'api_keys_configured': {
                'stackoverflow': bool(self.stackoverflow_api_key),
                'github': bool(self.github_token)
            }
        }