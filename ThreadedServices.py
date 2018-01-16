import threading
from RedditManager import RedditManager
from DatabaseManager import DatabaseManager
import RulesManager
from user import user
import time
import sys
import datetime
import prawcore


def setup_threads(subreddit):

    mod_monitor = ModeratorsMonitorThread(subreddit)

    rule_maint = RuleMaintenanceThread(subreddit)

    hot_monitor = HotMonitorThread(subreddit)

    user_stream = UserStreamThread()

    user_maint = UserMaintenanceThread()

    RedditManager.fetchCommentMetaRecent(subreddit)

    post_maint = PostMaintenanceThread()

    post_stream = PostStreamThread(subreddit)

    comment_stream = CommentStreamThread(subreddit)

    comment_maint = CommentMaintenanceThread()

    mod_monitor.start()

    rule_maint.start()

    hot_monitor.start()

    post_maint.start()

    user_stream.start()

    user_maint.start()

    post_stream.start()

    comment_stream.start()

    comment_maint.start()



class MessageMonitorThread(threading.Thread):

    def __init__(self):

        super().__init__(daemon=True)

        pass

    def run(self):



        pass

class ModeratorsMonitorThread(threading.Thread):

    def __init__(self, subreddit):
        super().__init__(daemon=True)

        self.subreddit = subreddit

    def run(self):

        userlist = RedditManager.get_subreddit_moderators(self.subreddit)

        DatabaseManager.update_moderators(userlist, self.subreddit)

        for mod in userlist:
            DatabaseManager.ensure_user_exists(mod.username, self.subreddit)

        #Sleep for 10 minutes
        time.sleep(10 * 60)

class HotMonitorThread(threading.Thread):

    def __init__(self, subreddit):
        super().__init__(daemon=True)

        self.subreddit = subreddit

    def run(self):

        MINUTE_DELAY = 60

        while True:

            # Get the current hot posts from the subreddit.

            front_posts = RedditManager.getFrontPage(subreddit=self.subreddit)

            count = 0

            for post in front_posts:
                count += 1
                DatabaseManager.update_post_rank(post.post_id, sub_rank=count)

            # Get the current hot posts from r/all
            filtered_dict = RedditManager.getFrontPageFiltered(subreddit='all', filtersub=self.subreddit)

            for rank, ranked_post in filtered_dict.items():

                DatabaseManager.update_post_rank(ranked_post.post_id, all_rank=rank)

                print(rank)

            #Sleep for 5 minutes before checking again.
            time.sleep(10)

class RuleMaintenanceThread(threading.Thread):

    """
    This class ensures the current rule set is being imposed and updates users based on changing states.
    """

    rule_page = "dfb-config"

    def __init__(self, subreddit):

        super().__init__(daemon=True)

        self.subreddit = subreddit

    def run(self):

        rule_page = RuleMaintenanceThread.rule_page

        while True:

            try:
                RulesManager.RulesManager.fetch_ruleset(subreddit=self.subreddit, page=rule_page)

                posts = DatabaseManager.get_all_posts(subreddit=self.subreddit)

                for a_post in posts:
                    RulesManager.RulesManager.evaluate_and_action(subreddit=self.subreddit, eval_post=a_post)

                users = DatabaseManager.get_all_users()

                for a_user in users:
                    RulesManager.RulesManager.evaluate_and_action(subreddit=self.subreddit, eval_user=a_user)

                RulesManager.RulesManager.commit_pending_batch_commands()

                pass

            except prawcore.exceptions.Forbidden as e:
                print("Need to be mod!")
                time.sleep(500)

class UserStreamThread(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)

    def run(self):

        print("User Stream Thread Started")

        while True:

            try:

                post_list = DatabaseManager.get_all_posts()

                for cur_post in post_list:

                    DatabaseManager.ensure_user_exists(cur_post.username, cur_post.subreddit)

                comment_list = DatabaseManager.get_all_comments()

                for cur_comment in comment_list:

                    DatabaseManager.ensure_user_exists(cur_comment.username, cur_comment.subreddit)


            except:

                print("User Stream Thread Exception: " + str(sys.exc_info()[0]))
                pass

class UserMaintenanceThread(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)

    def run(self):

        print("User Maintenance Thread Started")

        while True:

            try:

                user_list = DatabaseManager.get_all_users(limit=10)

                user_sub_list = []

                for cur_user in user_list:
                    cur_user.fetch()

                DatabaseManager.updateUserList(user_list)

            except:

                print("User Maintenance Thread Exception: " + str(sys.exc_info()[0]))

                pass

class PostStreamThread(threading.Thread):

    def __init__(self, subreddit=None):
        super().__init__(daemon=True)

        self.sub = subreddit

    def run(self):

        print("Post Stream Thread Started")

        if self.sub is None:
            return

        while True:
            metaList = RedditManager.fetchPostMetaRecent(self.sub)

            DatabaseManager.updatePostList(metaList)

            for post_meta in metaList:
                DatabaseManager.ensure_user_exists(post_meta.username, post_meta.subreddit)

            time.sleep(10)

            pass

class CommentStreamThread(threading.Thread):

    def __init__(self, subreddit=None):
        super().__init__(daemon=True)

        self.sub = subreddit

    def run(self):

        print("Comment Stream Thread Started")

        if self.sub is None:
            return

        while True:
            metaList = RedditManager.fetchCommentMetaRecent(self.sub)

            DatabaseManager.updateCommentList(metaList)

            for post_meta in metaList:
                DatabaseManager.ensure_user_exists(post_meta.username, post_meta.subreddit)

            time.sleep(10)

            pass

class PostMaintenanceThread(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)


    def run(self):

        print("Post Maintenance Thread Started")

        DAY_HALF_SECONDS = 60 * 60 * 24 * 1.5

        while True:

            try:

                current_time = datetime.datetime.utcnow().timestamp()

                post_list = DatabaseManager.get_all_posts(dateLimit=current_time - DAY_HALF_SECONDS)

                post_sub_list = []

                count = 0

                while count < len(post_list):

                    cur_post = post_list[count]

                    cur_post.fetch()

                    if count % 10 == 0:

                        DatabaseManager.updatePostList(post_sub_list)

                        post_sub_list = []

                    post_sub_list.append(post_list[count])

                    count += 1

            except:

                print("Post Main Thread Exception: " + str(sys.exc_info()[0]))

                pass

class CommentMaintenanceThread(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)


    def run(self):

        print("Comment Maintenance Thread Started")

        DAY_HALF_SECONDS = 60 * 60 * 24 * 1.5

        while True:

            try:

                current_time = datetime.datetime.utcnow().timestamp()

                comment_list = DatabaseManager.get_all_comments(dateLimit=current_time - DAY_HALF_SECONDS)

                comment_sub_list = []

                count = 0

                while count < len(comment_list):

                    comment_list[count].fetch()

                    if count % 10 == 0:

                        DatabaseManager.updateCommentList(comment_sub_list)

                        comment_sub_list = []

                    comment_sub_list.append(comment_list[count])

                    count += 1

            except:

                print("Comment Main Thread Exception: " + str(sys.exc_info()[0]))

                pass
