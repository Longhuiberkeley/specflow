--------------------------- MODULE IdAllocation_Current ---------------------------
\* valid as of 965ac21; not maintained.
\* SPIKE-003 part 2, fidelity canary: the CURRENT (pre-fix, HEAD 965ac21) index-store
\* protocol. TLC must find a safety violation here (defects A, B, C or E).
\* Disposable model. Not shipped, not a verify contract, never run in CI.
\*
\* Same encoding as IdAllocation.tla: canonical ids 1..MaxNum, drafts 101..;
\* `files` maps a file name to [id |-> frontmatter id, ino |-> inode].
\* Pre-fix behaviour modelled (git show 965ac21:src/specflow/lib/artifacts.py,
\* src/specflow/commands/renumber_drafts.py):
\*  - _read_index returns {keys {}, next 1} for a conflicted/unparsable index (A);
\*  - create allocates index next_id, checks duplicates against index keys only,
\*    and write_text replaces an existing file; only creates take the per-type lock;
\*  - update and rebuild-index read-modify-write the index without a lock (C);
\*  - rebuild sets next_id = max(ids on disk) + 1, ignoring quarantine/old next (B);
\*  - renumber-drafts takes no lock, plans from index next_id, rewrites, renames
\*    with Path.rename (replaces silently), then commits next_id (E).
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Actors, MaxNum, NDrafts, MaxIno, MaxCrashes, MergeKinds, Branches, Ops

Nums   == 1..MaxNum
Drafts == 101..(100 + NDrafts)
IsDraft(n) == n > 100
NumsIn(S) == {x \in S : ~IsDraft(x)}
Max(S) == IF S = {} THEN 0 ELSE CHOOSE x \in S : \A y \in S : x >= y
Min(S) == CHOOSE x \in S : \A y \in S : x <= y
None == "none"
NoMap == [x \in {} |-> 0]
Idx0 == [ok |-> TRUE, keys |-> {}, next |-> 1]
Loc0 == [idx |-> Idx0, map |-> NoMap, new |-> 0, ino |-> 0]

VARIABLES files, index, forkIdx, branch,
          clock,       \* the per-type create lock (creates only)
          pc, loc, allocated, reuse, clobber, dirty, crashes, nextIno, rnBad, draftsUsed

vars == <<files, index, forkIdx, branch, clock, pc, loc, allocated, reuse, clobber,
          dirty, crashes, nextIno, rnBad, draftsUsed>>

FmIds == {files[n].id : n \in DOMAIN files}
AllIdle == \A a \in Actors : pc[a] = "idle"
Put(f, n, c) == [m \in DOMAIN f \cup {n} |-> IF m = n THEN c ELSE f[m]]
Drop(f, n) == [m \in DOMAIN f \ {n} |-> f[m]]
\* pre-fix _read_index: anything unreadable becomes an empty index (defect A)
ReadIdx == IF index.ok THEN index ELSE Idx0

Init ==
  /\ files = [x \in {} |-> [id |-> 0, ino |-> 0]]
  /\ index = Idx0 /\ forkIdx = Idx0 /\ branch = "main" /\ clock = None
  /\ pc = [a \in Actors |-> "idle"] /\ loc = [a \in Actors |-> Loc0]
  /\ allocated = {} /\ reuse = FALSE /\ clobber = FALSE /\ dirty = FALSE
  /\ crashes = 0 /\ nextIno = 1 /\ rnBad = FALSE /\ draftsUsed = {}

---------------------------------------------------------------------------------
CRead(a) ==
  /\ "Create" \in Ops /\ pc[a] = "idle" /\ clock = None /\ nextIno <= MaxIno
  /\ LET I == ReadIdx
         cands == IF branch = "feature" THEN Drafts \ draftsUsed
                  ELSE IF I.next <= MaxNum /\ I.next \notin I.keys THEN {I.next} ELSE {}
     IN \E new \in cands :
          /\ clock' = a
          /\ pc' = [pc EXCEPT ![a] = "c_file"]
          /\ loc' = [loc EXCEPT ![a] =
                [idx |-> [ok |-> TRUE, keys |-> I.keys \cup {new},
                          next |-> IF IsDraft(new) THEN I.next ELSE new + 1],
                 map |-> NoMap, new |-> new, ino |-> nextIno]]
          /\ nextIno' = nextIno + 1
          /\ reuse' = (reuse \/ new \in allocated)
          /\ draftsUsed' = IF IsDraft(new) THEN draftsUsed \cup {new} ELSE draftsUsed
  /\ UNCHANGED <<files, index, forkIdx, branch, allocated, clobber, dirty, crashes, rnBad>>

CFile(a) ==
  /\ pc[a] = "c_file"
  /\ LET new == loc[a].new IN
       /\ clobber' = (clobber \/ new \in DOMAIN files)      \* write_text replaces
       /\ files' = Put(files, new, [id |-> new, ino |-> loc[a].ino])
  /\ pc' = [pc EXCEPT ![a] = "c_idx"]
  /\ UNCHANGED <<index, forkIdx, branch, clock, loc, allocated, reuse, dirty, crashes,
                 nextIno, rnBad, draftsUsed>>

CIdx(a) ==
  /\ pc[a] = "c_idx"
  /\ index' = loc[a].idx
  /\ allocated' = IF IsDraft(loc[a].new) THEN allocated ELSE allocated \cup {loc[a].new}
  /\ clock' = None /\ pc' = [pc EXCEPT ![a] = "idle"] /\ loc' = [loc EXCEPT ![a] = Loc0]
  /\ UNCHANGED <<files, forkIdx, branch, reuse, clobber, dirty, crashes, nextIno, rnBad,
                 draftsUsed>>

\* update: read the index, later write the stale copy back (no lock; defect C).
URead(a) ==
  /\ "Update" \in Ops /\ pc[a] = "idle" /\ index.ok /\ index.keys # {}
  /\ pc' = [pc EXCEPT ![a] = "u_write"]
  /\ loc' = [loc EXCEPT ![a].idx = index]
  /\ UNCHANGED <<files, index, forkIdx, branch, clock, allocated, reuse, clobber, dirty,
                 crashes, nextIno, rnBad, draftsUsed>>

UWrite(a) ==
  /\ pc[a] = "u_write"
  /\ index' = loc[a].idx
  /\ pc' = [pc EXCEPT ![a] = "idle"] /\ loc' = [loc EXCEPT ![a] = Loc0]
  /\ UNCHANGED <<files, forkIdx, branch, clock, allocated, reuse, clobber, dirty, crashes,
                 nextIno, rnBad, draftsUsed>>

\* rebuild-index: read disk, later write; next_id from disk only (defect B).
RRead(a) ==
  /\ "Rebuild" \in Ops /\ pc[a] = "idle"
  /\ pc' = [pc EXCEPT ![a] = "r_write"]
  /\ loc' = [loc EXCEPT ![a].idx = [ok |-> TRUE, keys |-> FmIds,
                                     next |-> Max(NumsIn(FmIds)) + 1]]
  /\ UNCHANGED <<files, index, forkIdx, branch, clock, allocated, reuse, clobber, dirty,
                 crashes, nextIno, rnBad, draftsUsed>>

RWrite(a) ==
  /\ pc[a] = "r_write"
  /\ index' = loc[a].idx /\ dirty' = FALSE
  /\ pc' = [pc EXCEPT ![a] = "idle"] /\ loc' = [loc EXCEPT ![a] = Loc0]
  /\ UNCHANGED <<files, forkIdx, branch, clock, allocated, reuse, clobber, crashes,
                 nextIno, rnBad, draftsUsed>>

---------------------------------------------------------------------------------
\* renumber-drafts, pre-fix: no lock, no branch refusal, no journal. A target counts
\* as allocated once a rewrite has written it somewhere (it is then durable). A
\* re-run re-planning a draft is judged by I1, I2 and I5, not by I3.
NPlan(a) ==
  /\ "Renumber" \in Ops /\ pc[a] = "idle"
  /\ LET I == ReadIdx
         DI == FmIds \cap Drafts
         map == [d \in DI |-> I.next - 1 + Cardinality({e \in DI : e <= d})]
     IN /\ DI # {}
        /\ I.next - 1 + Cardinality(DI) <= MaxNum
        /\ pc' = [pc EXCEPT ![a] = "n_rw"]
        /\ loc' = [loc EXCEPT ![a].map = map, ![a].new = I.next + Cardinality(DI)]
  /\ UNCHANGED <<files, index, forkIdx, branch, clock, allocated, reuse, clobber, dirty,
                 crashes, nextIno, rnBad, draftsUsed>>

NRewrite(a) ==
  /\ pc[a] = "n_rw"
  /\ LET M == loc[a].map
         W == {n \in DOMAIN files : files[n].id \in DOMAIN M}
         IK == index.keys \cap DOMAIN M
     IN IF W = {} /\ IK = {}
        THEN /\ pc' = [pc EXCEPT ![a] = "n_mv"]
             /\ UNCHANGED <<files, index, allocated>>
        ELSE /\ \/ \E n \in W : /\ files' = [files EXCEPT ![n].id = M[files[n].id]]
                                /\ allocated' = allocated \cup {M[files[n].id]}
                                /\ UNCHANGED index
                \/ /\ W = {} /\ IK # {}     \* code order: *.md first, then _index.yaml
                   /\ index' = [index EXCEPT !.keys = (@ \ DOMAIN M) \cup {M[k] : k \in IK}]
                   /\ allocated' = allocated \cup {M[k] : k \in IK}
                   /\ UNCHANGED files
             /\ UNCHANGED pc
  /\ UNCHANGED <<forkIdx, branch, clock, loc, reuse, clobber, dirty, crashes,
                 nextIno, rnBad, draftsUsed>>

\* Path.rename silently replaces an existing target.
NMove(a) ==
  /\ pc[a] = "n_mv"
  /\ LET M == loc[a].map
         S == DOMAIN files \cap DOMAIN M
     IN IF S = {}
        THEN /\ pc' = [pc EXCEPT ![a] = "n_commit"]
             /\ UNCHANGED <<files, clobber>>
        ELSE LET n == Min(S)
                 t == M[n]
             IN /\ clobber' = (clobber \/ (t \in DOMAIN files /\ files[t].ino # files[n].ino))
                /\ files' = Put(Drop(files, n), t, files[n])
                /\ UNCHANGED pc
  /\ UNCHANGED <<index, forkIdx, branch, clock, loc, allocated, reuse, dirty, crashes,
                 nextIno, rnBad, draftsUsed>>

Converged(M) == \A n \in DOMAIN files : files[n].id = n /\ n \notin DOMAIN M

\* _commit_indexes + _refresh_indexes: read, set next_id, write.
NCommit(a) ==
  /\ pc[a] = "n_commit"
  /\ index' = [ReadIdx EXCEPT !.next = loc[a].new]
  /\ rnBad' = (rnBad \/ ~Converged(loc[a].map))
  /\ pc' = [pc EXCEPT ![a] = "idle"] /\ loc' = [loc EXCEPT ![a] = Loc0]
  /\ UNCHANGED <<files, forkIdx, branch, clock, allocated, reuse, clobber, dirty, crashes,
                 nextIno, draftsUsed>>

---------------------------------------------------------------------------------
Crash(a) ==
  /\ "Crash" \in Ops /\ pc[a] # "idle" /\ crashes < MaxCrashes
  /\ crashes' = crashes + 1 /\ dirty' = TRUE
  /\ clock' = IF clock = a THEN None ELSE clock   \* the create lock file is left; a
                                                 \* stale break frees it (modelled free)
  /\ pc' = [pc EXCEPT ![a] = "idle"] /\ loc' = [loc EXCEPT ![a] = Loc0]
  /\ UNCHANGED <<files, index, forkIdx, branch, allocated, reuse, clobber, nextIno,
                 rnBad, draftsUsed>>

Delete ==
  /\ "Delete" \in Ops /\ AllIdle     \* hand edits happen between commands
  /\ \E n \in DOMAIN files : files' = Drop(files, n)
  /\ dirty' = TRUE
  /\ UNCHANGED <<index, forkIdx, branch, clock, pc, loc, allocated, reuse, clobber,
                 crashes, nextIno, rnBad, draftsUsed>>

Fork ==
  /\ "GitMerge" \in Ops /\ AllIdle /\ index.ok /\ forkIdx # index
  /\ forkIdx' = index
  /\ UNCHANGED <<files, index, branch, clock, pc, loc, allocated, reuse, clobber, dirty,
                 crashes, nextIno, rnBad, draftsUsed>>

GitMerge ==
  /\ "GitMerge" \in Ops /\ AllIdle /\ index.ok /\ nextIno <= MaxIno
  /\ \E d \in Drafts \ draftsUsed, k \in MergeKinds :
       LET theirs == [ok |-> TRUE, keys |-> forkIdx.keys \cup {d}, next |-> forkIdx.next]
           union  == [ok |-> TRUE, keys |-> index.keys \cup theirs.keys,
                      next |-> Max({index.next, theirs.next})]
       IN /\ index' = CASE k = "Ours"     -> index
                        [] k = "Theirs"   -> theirs
                        [] k = "Union"    -> union
                        [] k = "Conflict" -> [union EXCEPT !.ok = FALSE]
          /\ files' = Put(files, d, [id |-> d, ino |-> nextIno])
          /\ nextIno' = nextIno + 1
          /\ draftsUsed' = draftsUsed \cup {d}
          /\ dirty' = TRUE
  /\ UNCHANGED <<forkIdx, branch, clock, pc, loc, allocated, reuse, clobber, crashes,
                 rnBad>>

BranchKind ==
  /\ "Branch" \in Ops /\ AllIdle
  /\ \E b \in Branches : b # branch /\ branch' = b
  /\ UNCHANGED <<files, index, forkIdx, clock, pc, loc, allocated, reuse, clobber, dirty,
                 crashes, nextIno, rnBad, draftsUsed>>

Next ==
  \/ \E a \in Actors : \/ CRead(a) \/ CFile(a) \/ CIdx(a) \/ URead(a) \/ UWrite(a)
                       \/ RRead(a) \/ RWrite(a) \/ NPlan(a) \/ NRewrite(a) \/ NMove(a)
                       \/ NCommit(a) \/ Crash(a)
  \/ Delete \/ Fork \/ GitMerge \/ BranchKind

Spec == Init /\ [][Next]_vars

---------------------------------------------------------------------------------
I1_NoDupId == \A m, n \in DOMAIN files :
                 (m # n /\ files[m].id = files[n].id) => files[m].ino = files[n].ino
I2_NoOverwrite == ~clobber
I3_NoReuse == ~reuse
I4_IndexIsCache == (AllIdle /\ ~dirty /\ index.ok) =>
                     /\ index.keys = FmIds
                     /\ (allocated = {} \/ index.next > Max(allocated))
I5_RerunConverges == ~rnBad

Perms == Permutations(Actors)
=================================================================================
