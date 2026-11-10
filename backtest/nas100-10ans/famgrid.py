import sys; sys.path.insert(0, ".")
import itertools, json, multiprocessing as mp
import numpy as np
import fam
def init():
    fam.prep()
def work(job):
    fname, p = job
    out = (fam.orb if fname == "orb" else fam.cont)(p)
    s = fam.stats(out)
    s.pop("yrs", None)
    q = {k: (sorted(v) if isinstance(v, set) else v) for k, v in p.items()}
    return dict(f=fname, p=q, **{k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in s.items()})
jobs = []
for orMin, entry, stop, rr, maxT, cut in itertools.product((5, 15, 30, 60), ("close", "stop"), ("range", "mid"),
                                                          (1.0, 1.5, 2.0, 3.0, 5.0, None), (1, 2), (660, 720, 900)):
    jobs.append(("orb", dict(orMin=orMin, entry=entry, stop=stop, rr=rr, maxT=maxT, cutoff=cut)))
for pools, sess, disp, entry, stop, rr in itertools.product(({"asia"}, {"asia", "pd"}, {"asia", "pd", "lon"}), ({0}, {1}, {0, 1}),
                                                            (0.0, 0.5, 1.0), ("close", "retest", "mid"), ("candle", "swing"), (1.0, 2.0, 3.0, None)):
    jobs.append(("cont", dict(pools=pools, sess=sess, disp=disp, entry=entry, stop=stop, rr=rr, maxT=2)))
if __name__ == "__main__":
    with mp.Pool(4, initializer=init) as pool:
        res = pool.map(work, jobs, chunksize=4)
    json.dump(res, open("famgrid.json", "w"))
    print(len(res))
