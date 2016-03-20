"""Provide the Subreddit class."""
from ...const import API_PATH
from ..listing.generator import ListingGenerator
from ..listing.mixins import SubredditListingMixin
from .base import RedditBase
from .mixins import MessageableMixin


class Subreddit(RedditBase, MessageableMixin, SubredditListingMixin):
    """A class for Subreddits."""

    EQ_FIELD = 'display_name'

    def __init__(self, reddit, display_name=None, _data=None):
        """Initialize a Subreddit instance.

        :param reddit: An instance of :class:`~.Reddit`.
        :param display_name: The name of the subreddit.

        """
        if bool(display_name) == bool(_data):
            raise TypeError(
                'Either `display_name` or `_data` must be provided.')
        super(Subreddit, self).__init__(reddit, _data)
        if display_name:
            self.display_name = display_name
        self._path = API_PATH['subreddit'].format(subreddit=self.display_name)
        self._prepare_relationships()
        self.flair = SubredditFlair(self)
        self.mod = SubredditModeration(self)

    def _info_path(self):
        return API_PATH['subreddit_about'].format(subreddit=self.display_name)

    def _prepare_relationships(self):
        for relationship in ['banned', 'contributor', 'moderator', 'muted',
                             'wikibanned', 'wikicontributor']:
            setattr(self, relationship,
                    SubredditRelationship(self, relationship))

    def submit(self, title, selftext=None, url=None, resubmit=True,
               send_replies=True):
        """Add a submission to the subreddit.

        :param title: The title of the submission.
        :param selftext: The markdown formatted content for a ``text``
            submission.
        :param url: The URL for a ``link`` submission.
        :param resubmit: When False, an error will occur if the URL has already
            been submitted (Default: True).
        :param send_replies: When True, messages will be sent to the submission
            author when comments are made to the submission (Default: True).
        :returns: A :class:`~.Submission` object for the newly created
            submission.

        Either ``selftext`` or ``url`` can be provided, but not both.

        """
        if bool(selftext) == bool(url):
            raise TypeError('Either `selftext` or `url` must be provided.')

        data = {'sr': str(self), 'resubmit': bool(resubmit),
                'sendreplies': bool(send_replies), 'title': title}
        if selftext is not None:
            data.update(kind='self', text=selftext)
        else:
            data.update(kind='link', url=url)
        return self._reddit.post(API_PATH['submit'], data=data)


class SubredditFlair(object):
    """Provides a set of functions to interact with a Subreddit's flair."""

    def __init__(self, subreddit):
        """Create a SubredditFlair instance.

        :param subreddit: The subreddit whose flair to work with.

        """
        self._unique_counter = 0
        self.subreddit = subreddit

    def __iter__(self):
        """Iterate through the Redditors and their associated flair."""
        url = API_PATH['flairlist'].format(subreddit=str(self.subreddit))
        params = {'unique': self._unique_counter}
        self._unique_counter += 1
        for item in ListingGenerator(self.subreddit._reddit, url, None,
                                     params=params):
            yield item

    """
    def clear_all(self, subreddit):
        emove all user flair on ``subreddit``.

        :param subreddit: The Subreddit to remove all flair from..

        csv = [{'user': x['user']} for x in self]
        print(csv)
        self.csv(csv)
    """

    def set(self, thing, text='', css_class=''):
        """Set flair for a Redditor or Submission.

        :param thing: An instance of Redditor or Submission, or a string. When
            a string is provided it will be treated as the name of a Redditor.
        :param text: The flair text to associate with the Redditor or
            Submission (Default: '').
        :param css_class: The css class to associate with the flair html
            (Default: '').

        This method can only be used by an authenticated user who is a
        moderator of the associated Subreddit.

        """
        data = {'css_class': css_class, 'text': text}
        if thing.__class__.__name__ == 'Submission':
            data['link'] = thing.fullname
        else:
            data['name'] = str(thing)
        url = API_PATH['flair'].format(subreddit=self.subreddit)
        self.subreddit._reddit.post(url, data=data)


class SubredditModeration(object):
    """Provides a set of moderation functions to a Subreddit."""

    def __init__(self, subreddit):
        """Create a SubredditModeration instance.

        :param subreddit: The subreddit to moderate.

        """
        self.subreddit = subreddit

    def approve(self, thing):
        """Approve a Comment or Submission.

        :param thing: An instance of Comment or Submission.

        Approving a comment or submission reverts a removal, resets the report
        counter, adds a green check mark indicator (only visible to other
        moderators) on the website view, and sets the ``approved_by`` attribute
        to the authenticated user.

        """
        self.subreddit._reddit.post(API_PATH['approve'],
                                    data={'id': thing.fullname})

    def distinguish(self, thing, how='yes'):
        """Distinguish a Comment or Submission.

        :param thing: An instance of Comment or Submission.

        :param how: One of 'yes', 'no', 'admin', 'special'. 'yes' adds a
            moderator level distinguish. 'no' removes any distinction. 'admin'
            and 'special' require special user priviliges to use.

        """
        return self.subreddit._reddit.post(
            API_PATH['distinguish'], data={'how': how, 'id': thing.fullname})

    def ignore_reports(self, thing):
        """Ignore future reports on a Comment or Submission.

        :param thing: An instance of Comment or Submission.

        Calling this method will prevent future reports on this Comment or
        Submission from both triggering notifications and appearing in the
        various moderation listings. The report count will still increment on
        the Comment or Submission.

        """
        self.subreddit._reddit.post(API_PATH['ignore_reports'],
                                    data={'id': thing.fullname})

    def remove(self, thing, spam=False):
        """Remove a Comment or Submission.

        :param thing: An instance of Comment or Submission.
        :param spam: When True, use the removal to help train the Subreddit's
            spam filter (Default: False)

        """
        data = {'id': thing.fullname, 'spam': bool(spam)}
        self.subreddit._reddit.post(API_PATH['remove'], data=data)

    def undistinguish(self, thing):
        """Remove mod, admin or special distinguishing on object.

        :returns: The json response from the server.

        """
        return self.distinguish(thing, how='no')

    def unignore_reports(self, thing):
        """Resume receiving future reports on a Comment or Submission.

        :param thing: An instance of Comment or Submission.

        Future reports on this Comment or Submission will cause notifications,
        and appear in the various moderation listings.

        """
        self.subreddit._reddit.post(API_PATH['unignore_reports'],
                                    data={'id': thing.fullname})


class SubredditRelationship(object):
    """Represents a relationship between a redditor and subreddit."""

    def __init__(self, subreddit, relationship):
        """Create a SubredditRelationship instance.

        :param subreddit: The subreddit for the relationship.
        :param relationship: The name of the relationship.

        """
        self.relationship = relationship
        self.subreddit = subreddit
        self._unique_counter = 0

    def __iter__(self):
        """Iterate through the Redditors belonging to this relationship."""
        url = API_PATH[self.relationship].format(subreddit=str(self.subreddit))
        params = {'unique': self._unique_counter}
        self._unique_counter += 1
        for item in self.subreddit._reddit.get(url, params=params):
            yield item

    def add(self, redditor):
        """Add ``redditor`` to this relationship.

        :param redditor: A string or :class:`~.Redditor` instance.

        """
        data = {'name': str(redditor), 'r': str(self.subreddit),
                'type': self.relationship}
        return self.subreddit._reddit.post(API_PATH['friend'], data=data)

    def remove(self, redditor):
        """Remove ``redditor`` from this relationship.

        :param redditor: A string or :class:`~.Redditor` instance.

        """
        data = {'name': str(redditor), 'r': str(self.subreddit),
                'type': self.relationship}
        return self.subreddit._reddit.post(API_PATH['unfriend'], data=data)
