def create_quiz_from_youtube_url(video_url):
    """Generate quiz content from a YouTube URL.

    This lightweight implementation is intentionally local and mock-friendly.
    """

    return {
        'title': 'Generated Quiz',
        'description': f'Generated from {video_url}',
        'questions': [],
    }
