from subprocess import check_output
import xml.etree.ElementTree as ET
from pathlib import Path
import sys
import os
import re
import argparse

def parseArgs():
    parser = argparse.ArgumentParser(description='git history change information.')
    parser.add_argument('--repo', help='repo path')
    parser.add_argument('-e', nargs='+', help='search string')
    return parser.parse_args()

class UserCodeChangeInfo:
    def __init__(self, commit_id = "", user_info = "", date_info = "", pr_info = "", commit_info = "", code_changes = {}):
        self.commit_id = commit_id
        self.date_info = date_info
        self.user_info = user_info
        self.pr_info = pr_info
        self.commit_info = commit_info
        self.code_changes = code_changes


def whiteToXmlFile(userCodeChangeInfos, path):
    # create the file structure
    code_change = ET.Element('Code Change')
    for commit_id, userCodeChangeInfo in userCodeChangeInfos.items():
        element_commit = ET.SubElement(code_change, 'commit', {"id" : commit_id})
        ET.SubElement(element_commit, "commit_id").text = userCodeChangeInfo.commit_id
        ET.SubElement(element_commit, "date").text = userCodeChangeInfo.date_info
        ET.SubElement(element_commit, "user").text = userCodeChangeInfo.user_info
        ET.SubElement(element_commit, "pr").text = userCodeChangeInfo.pr_info
        element_code_changes = ET.SubElement(element_commit, "code")
        for file_path, code_changes in userCodeChangeInfo.code_changes.items():
            element_file_path = ET.SubElement(element_code_changes, "file path", {"file" : file_path})
            for change in code_changes:
                ET.SubElement(element_file_path, "change").text = change

    mydata = ET.tostring(code_change)
    myfile = open(os.path.join(path, "code_change_history.xml"), "w")
    myfile.write(mydata.decode("utf-8"))

def findStringInRepo(args):
    repo_path = args["repo"]
    os.chdir(repo_path)
    cmd = ['git', 'grep']
    search_strings = args["e"]
    for element in search_strings:
        cmd.append('-e')
        cmd.append(element)

    print(cmd)
    grep_output = check_output(cmd).decode("utf-8")

    grep_lines = grep_output.splitlines()
    file_paths = []
    user_code_change_infos = {}
    for grep_line in grep_lines:
        file_path = re.split(":\s*", grep_line, 1)
        file_paths.append(file_path)
    for val in file_paths:
        file_path = val[0]
        code_change = val[1]
        git_blame_output = check_output(["git",  "blame", file_path]).decode("utf-8")

        blame_lines = git_blame_output.splitlines()

        for blame_line in blame_lines:
            if code_change in blame_line:
                commit_id = re.split("\s", blame_line, 1)[0]
                user_code_change = user_code_change_infos.get(commit_id)
                if user_code_change is None:
                    user_code_change_infos[commit_id] = UserCodeChangeInfo(commit_id, "", "", "", "", {file_path : [code_change]})
                else:
                    file_code_changes = user_code_change.code_changes.get(file_path)
                    if file_code_changes is None:
                        user_code_change.code_changes[file_path] = [code_change]
                    else:
                        user_code_change.code_changes[file_path].append(code_change)

        for commit_id, user_code_change in user_code_change_infos.items():
            commit_info = check_output(["git", "log", commit_id, "-n 1"]).decode("utf-8")
            user_code_change.commit_info = commit_info

            git_log_n1_lines = commit_info.splitlines()
            user_code_change.commit_id = git_log_n1_lines[0]
            user_code_change.user_info = git_log_n1_lines[1]
            user_code_change.date_info = git_log_n1_lines[2]
            pr_number = re.findall(r'\(#(\d*)\)', git_log_n1_lines[4])[-1]
            user_code_change.pr_info = "https://sqbu-github.cisco.com/WebExSquared/spark-client-framework/pull/{}".format(pr_number)

    print("====================================================================")
    for commit_id, user_code_change in user_code_change_infos.items():
        print("commitId:", commit_id)
        print("user:", user_code_change.user_info)
        print("pr", user_code_change.pr_info)
        print("change:", user_code_change.code_changes)
        print("====================================================================")
    return user_code_change_infos


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    args = vars(parseArgs())
    userCodeChangeInfos = findStringInRepo(args)
    whiteToXmlFile(userCodeChangeInfos, Path(args["repo"]).parent.absolute())

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
