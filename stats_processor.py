import sqlite3
import json
import sys
import numpy as np

def error_print(error):
    print error
    sys.stdin.flush()

def get_orig(db, stream_id, offset, limit):
    res = []
    sql = "select message from log where stream_id = {0} and logger = 'DataAPIStats' order by id limit {1} offset {2}".format(stream_id,
                                                                                                                               limit,
                                                                                                                               offset)
    done = False
    while not done:
        try:
            cursor.execute(sql)
            done = True
        except sqlite3.OperationalError as e:
            print e
            error_print("locked, retrying")

    for row in cursor.fetchall():
        message = row[0]
        try:
            idx = message.index("(delayed from")
            message = row[0]
            message = message[:idx]
        except ValueError:
            pass

        try:
            idx1 = message.index('{"f":"topics:"')
            tmp = message[idx1:-1]
            idx1a = tmp.index('}')
            idx2 = idx1+idx1a + 1
            tmp2 = message[idx1:idx2]
            #print "_____________"
            #print tmp2
            last_item = None
            new_list = []
            for item in tmp2.split(':'):
                #print item
                if last_item == '"topics':
                    if item[0] == '"':
                        item = item[1:]
                    tmp3 = item.split(',')
                    if tmp3[0][-2:] == '""':
                        tmp3[0] = tmp3[0][:-1]
                        item = ','.join(tmp3)
                new_list.append(item)
                last_item = item
            new_stuff = ':'.join(new_list)
            message = message[:idx1] + new_stuff + message[idx2:]
            #print message
            #print "_____________"
        except ValueError as e:
            pass
        try:
            data = json.loads(message)
        except ValueError as e:
            print message
            import ipdb;ipdb.set_trace()
            raise
        res.append(data)

    return res


class OnlineVariance(object):
    """
    Welford's algorithm computes the sample variance incrementally.
    """

    def __init__(self, iterable=None):
        self.n = 0.0
        self.mean = 0.0
        self.M2 = 0.0
        self.max = 0
        self.min = 111111111111111111
        if iterable is not None:
            for datum in iterable:
                self.include(datum)

    def include(self, datum):
        self.n += 1
        self.delta = datum - self.mean
        self.mean += self.delta / self.n
        self.M2 += self.delta * (datum - self.mean)
        if self.n > 2:
            self.variance = self.M2 / (self.n - 1)
        self.min = min(self.min, datum)
        self.max = max(self.max, datum)

    @property
    def std(self):
        return np.sqrt(self.variance)

if __name__=="__main__":
    stream_id = 0

    if len(sys.argv) > 1:
        db_name = sys.argv[1]
    else:
        db_name = 'log_data.sqlite3'

    db = sqlite3.connect(db_name)
    cursor = db.cursor()

    if len(sys.argv) > 2:
        stream_id = int(sys.argv[2])
    else:
        sql = "select stream_id from last_stream"
        cursor.execute(sql)
        row =  cursor.fetchone()
        stream_id = row[0]


    item_count = 10000
    items = get_orig(db, stream_id, 1, item_count)
    ov = OnlineVariance()
    d_list = []
    s_list = []
    for item in items:
        data = float(item["requestElapsed"]) / 1000.0
        ov.include(data)
        d_list.append(data)
        s_list.append(str(data))
        if item_count <= 20:
            print data
        if len(d_list) == 1:
            print "first record"
            print json.dumps(item, indent=4)
        if len(d_list) == len(items):
            print "last record"
            print json.dumps(item, indent=4)
    std = ov.std
    print("variance = {5}, std={0}, std2 = {6}, mean={1}, samples={2}, max={3}, min={4}".format(std, ov.mean, ov.n, ov.max, ov.min, ov.variance, std/ov.mean))


    if item_count <= 20:
        print ','.join(s_list)
    import numpy as np

    bin_count = 10
    print("numpy std",  np.std(d_list))
    print("numpy var", np.var(d_list))
    print("numpy mean", np.mean(d_list))
    hist = np.histogram(d_list, bins=bin_count)
    print hist
    fmt = "{0} to {1} seconds, {2} hits, {3}%"
    for i in range(bin_count):
        hits =  hist[0][i]
        per = hits/float(len(d_list))
        if i == bin_count - 1:
            print(fmt.format(hist[1][i], 'infinity', hits, per))
        else:
            print(fmt.format(hist[1][i], hist[1][i+1], hits, per))
    try:
        import matplotlib.pyplot as plt
        plt.hist(d_list, bins=bin_count)
        plt.show()
    except ImportError:
        pass
