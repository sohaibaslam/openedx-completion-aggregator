"""
Asynchronous tasks.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from collections import namedtuple
from datetime import datetime

import pytz
from celery import shared_task
from xblock.completable import XBlockCompletionMode
from xblock.core import XBlock

from . import compat
from .models import Aggregator

OLD_DATETIME = pytz.utc.localize(datetime(1900, 1, 1, 0, 0, 0))

log = logging.getLogger(__name__)


CompletionStats = namedtuple('CompletionStats', ['earned', 'possible', 'last_modified'])  # pylint: disable=invalid-name


@shared_task
def update_aggregators(user, course_key, block_keys=frozenset(), force=False):  # pylint: disable=unused-argument
    """
    Update aggregators for the specified course.

    Takes a collection of block_keys that have been updated, to enable
    future optimizations in how aggregators are recalculated.
    """
    from xmodule.modulestore.django import modulestore   # pylint: disable=import-error

    log.warning("Updating aggregators in %s for %s", course_key, user)

    updater = AggregationUpdater(user, course_key, modulestore())
    updater.update(block_keys, force)


class AggregationUpdater(object):
    """
    Class to update aggregators for a given course and user.
    """

    def __init__(self, user, course_key, modulestore):
        """
        Create an aggregation updater for the given user and course.

        Also takes a modulestore instance.
        """
        self.user = user
        self.course_key = course_key

        with modulestore.bulk_operations(self.course_key):
            self.course_block_key = compat.init_course_block_key(modulestore, self.course_key)
            self.course_blocks = compat.init_course_blocks(self.user, self.course_block_key)
        self.aggregators = {
            aggregator.block_key: aggregator for aggregator in Aggregator.objects.filter(
                user=self.user,
                course_key=self.course_key,
            )
        }
        self.block_completions = {
            completion.block_key: completion for completion in compat.get_block_completions(self.user, self.course_key)
        }

    def update(self, changed_blocks=frozenset(), force=False):
        """
        Update the aggregators for the course.

        Takes a set of completable blocks that have been recently updated to
        inform how to perform the update.  Currently no optimizations are
        performed based on this information, but in the future they may help
        cut down on the amount of work performed.
        """
        self.update_for_block(self.course_block_key, changed_blocks, force)

    def update_for_block(self, block, changed_blocks, force=False):
        """
        Recursive function to perform updates for a given block.

        Dispatches to an appropriate method given the block's completion_mode.
        """
        mode = getattr(XBlock.load_class(block.block_type), 'completion_mode', XBlockCompletionMode.COMPLETABLE)
        if mode == XBlockCompletionMode.EXCLUDED:
            return self.update_for_excluded()
        elif mode == XBlockCompletionMode.COMPLETABLE:
            return self.update_for_completable(block, changed_blocks)
        elif mode == XBlockCompletionMode.AGGREGATOR:
            return self.update_for_aggregator(block, changed_blocks, force)

    def update_for_aggregator(self, block, changed_blocks, force):
        """
        Calculate the new completion values for an aggregator.
        """
        total_earned = 0.0
        total_possible = 0.0
        last_modified = OLD_DATETIME
        for child in compat.get_children(self.course_blocks, block):
            (earned, possible, modified) = self.update_for_block(child, changed_blocks, force)
            total_earned += earned
            total_possible += possible
            last_modified = max(last_modified, modified)
        if self._aggregator_needs_update(block, last_modified, force):
            log.warning("updating aggregator %s", block)
            Aggregator.objects.submit_completion(
                user=self.user,
                course_key=self.course_key,
                block_key=block,
                aggregation_name=block.block_type,
                earned=total_earned,
                possible=total_possible,
                last_modified=last_modified,
            )
        return CompletionStats(earned=total_earned, possible=total_possible, last_modified=last_modified)

    def update_for_excluded(self):
        """
        Return a sentinel empty completion value for excluded blocks.
        """
        return CompletionStats(earned=0.0, possible=0.0, last_modified=OLD_DATETIME)

    def update_for_completable(self, block, changed_blocks):  # pylint: disable=unused-argument
        """
        Return the block completion value for a given completable block.
        """
        completion = self.block_completions.get(block)
        if completion:
            earned = completion.completion
            last_modified = completion.modified
        else:
            earned = 0.0
            last_modified = OLD_DATETIME
        return CompletionStats(earned=earned, possible=1.0, last_modified=last_modified)

    def _aggregator_needs_update(self, block, modified, force):
        """
        Return True if the given aggregator block needs to be updated.

        This method assumes that the block has already been determined to be an aggregator.
        """
        if Aggregator.block_is_registered_aggregator(block):
            agg = self.aggregators.get(block)
            if force:
                return True
            return getattr(agg, 'last_modified', OLD_DATETIME) < modified
        return False