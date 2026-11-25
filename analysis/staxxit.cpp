#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace staxxit {
constexpr int N = 127;
struct Move {
  char t;
  int p, q, k;
};
struct Stack {
  uint64_t bits = 0;
  uint8_t h = 0;
  int owner() const { return int((bits >> (h - 1)) & 1); }
};
struct State {
  std::array<Stack, N> b{};
  int res[2] = {18, 18};
  int side = 0, passes = 0;
};
struct Geometry {
  std::array<std::array<int, 2>, N> pos{};
  std::array<int, N> outer{};
  std::array<std::array<std::vector<int>, 6>, N> rays;
  std::array<std::vector<int>, N> neighbors;
  std::array<std::array<int, N>, N> distance{};
  int index[13][13], center = 0;
  static int norm(int q, int r) {
    return std::max({std::abs(q), std::abs(r), std::abs(q + r)});
  }
  Geometry() {
    for (auto& a : index) std::fill(std::begin(a), std::end(a), -1);
    int n = 0;
    for (int q = -6; q <= 6; q++)
      for (int r = -6; r <= 6; r++)
        if (norm(q, r) <= 6) {
          index[q + 6][r + 6] = n;
          pos[n++] = {q, r};
        }
    center = index[6][6];
    outer.fill(-1);
    int q = 6, r = 0, c = 0;
    const int ring[6][2] = {{-1, 1}, {-1, 0}, {0, -1}, {1, -1}, {1, 0}, {0, 1}};
    for (auto& d : ring)
      for (int j = 0; j < 6; j++) {
        outer[index[q + 6][r + 6]] = j ? c : 2;
        if (j) c = 1 - c;
        q += d[0];
        r += d[1];
      }
    const int ds[6][2] = {{1, 0}, {1, -1}, {0, -1}, {-1, 0}, {-1, 1}, {0, 1}};
    for (int p = 0; p < N; p++) {
      for (int d = 0; d < 6; d++)
        for (int k = 1; k <= 12; k++) {
          int x = pos[p][0] + k * ds[d][0], y = pos[p][1] + k * ds[d][1];
          if (norm(x, y) > 6) break;
          rays[p][d].push_back(index[x + 6][y + 6]);
        }
      for (auto& ray : rays[p])
        if (!ray.empty() && outer[ray[0]] < 0) neighbors[p].push_back(ray[0]);
      for (int t = 0; t < N; t++)
        distance[p][t] = norm(pos[p][0] - pos[t][0], pos[p][1] - pos[t][1]);
    }
  }
} const geo;

uint64_t mix(uint64_t x) {
  x += 0x9e3779b97f4a7c15ULL;
  x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
  x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
  return x ^ (x >> 31);
}
struct RNG {
  uint64_t x;
  uint64_t next() {
    x += 0x9e3779b97f4a7c15ULL;
    uint64_t z = x;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
  }
  uint64_t bounded(uint64_t n) {
    const uint64_t threshold = -n % n;
    for (;;) {
      auto z = next();
      if (z >= threshold) return z % n;
    }
  }
};
uint64_t mask(int k) { return k ? ((uint64_t(1) << k) - 1) : 0; }
int popcount(uint64_t x) {
  int n = 0;
  while (x) {
    x &= x - 1;
    n++;
  }
  return n;
}
void conservation(const State& s) {
  int totals[2] = {s.res[0], s.res[1]};
  for (const auto& st : s.b) {
    if (st.h > 36 || (st.bits & ~mask(st.h)))
      throw std::runtime_error("invalid bit stack");
    int n = popcount(st.bits);
    totals[1] += n;
    totals[0] += st.h - n;
  }
  if (totals[0] != 18 || totals[1] != 18)
    throw std::runtime_error("stone conservation failure");
}
std::vector<Move> legal(const State& s, bool v) {
  int c = s.side;
  bool placing = s.res[c] > 0,
       full = !placing && (v || (!s.res[0] && !s.res[1]));
  std::vector<Move> places, caps, moves;
  places.reserve(64);
  caps.reserve(16);
  moves.reserve(256);
  if (placing) {
    std::array<bool, N> cand{};
    bool active = false;
    for (int p = 0; p < N; p++)
      if (geo.outer[p] < 0 && s.b[p].h) {
        active = true;
        for (int t : geo.neighbors[p])
          if (!s.b[t].h) cand[t] = true;
      }
    if (!active) cand[geo.center] = true;
    for (int t = 0; t < N; t++)
      if (cand[t]) places.push_back({'p', -1, t, 0});
    if (!v) return places;
  }
  if (!full && !placing) return {};
  for (int p = 0; p < N; p++) {
    const auto& st = s.b[p];
    if (geo.outer[p] >= 0 || !st.h || st.owner() != c) continue;
    int h = st.h;
    for (const auto& ray : geo.rays[p]) {
      for (int i = 0; i < h && i < int(ray.size()); i++) {
        int t = ray[i];
        if (s.b[t].h) {
          if (i + 1 == h && geo.outer[t] < 0 && s.b[t].owner() != c)
            caps.push_back({'c', p, t, 0});
          break;
        }
        if (geo.outer[t] >= 0) {
          if (full && i + 1 == h && (geo.outer[t] == c || geo.outer[t] == 2))
            moves.push_back({'e', p, t, 0});
          break;
        }
        if (full) moves.push_back({'m', p, t, 0});
      }
      if (full && h >= 12 && !ray.empty() && geo.outer[ray[0]] < 0 &&
          !s.b[ray[0]].h)
        for (int k = 1; k < h; k++)
          if (((st.bits >> (k - 1)) & 1) == unsigned(c))
            moves.push_back({'s', p, ray[0], k});
    }
  }
  if (placing) {
    places.insert(places.end(), caps.begin(), caps.end());
    return places;
  }
  return caps.empty() ? moves : caps;
}
void step(State& s, Move a) {
  auto& t = s.b[a.q];
  if (a.t == 'p') {
    t.bits = s.side;
    t.h = 1;
    s.res[s.side]--;
    return;
  }
  auto& f = s.b[a.p];
  int k = a.t == 's' ? a.k : 0;
  t.bits |= (f.bits >> k) << t.h;
  t.h = uint8_t(t.h + f.h - k);
  f.bits &= mask(k);
  f.h = uint8_t(k);
}
int result(const State& s, bool v) {
  if (!v && (s.res[0] || s.res[1])) return -1;
  bool active[2] = {};
  std::pair<int, int> score[2] = {};
  for (int p = 0; p < N; p++)
    if (s.b[p].h) {
      int c = s.b[p].owner();
      if (geo.outer[p] < 0)
        active[c] = true;
      else {
        score[c].first++;
        score[c].second += s.b[p].h;
      }
    }
  if ((s.res[0] || active[0]) && (s.res[1] || active[1])) return -1;
  return score[0] > score[1] ? 0 : score[1] > score[0] ? 1 : 2;
}
std::string key(const State& s) {
  std::string k;
  k.reserve(116);
  k.push_back(char(s.side));
  k.push_back(char(s.res[0]));
  k.push_back(char(s.res[1]));
  k.push_back(char(s.passes));
  for (int p = 0; p < N; p++)
    if (s.b[p].h) {
      k.push_back(char(p));
      k.push_back(char(s.b[p].h));
      uint64_t bits = s.b[p].bits;
      for (int n = 0; n < s.b[p].h; n += 8) {
        k.push_back(char(bits & 255));
        bits >>= 8;
      }
    }
  return k;
}
bool empty_inside(const State& s) {
  for (int p = 0; p < N; p++)
    if (geo.outer[p] < 0 && s.b[p].h) return false;
  return true;
}

// Placement heuristics use stack ownership (the top stone), never buried
// colour.
double placement_score(const State& s, int t, int strategy) {
  int c = s.side, own = 0, enemy = 0;
  for (int n : geo.neighbors[t]) {
    if (!s.b[n].h) continue;
    if (s.b[n].owner() == c)
      own++;
    else
      enemy++;
  }
  int radius = Geometry::norm(geo.pos[t][0], geo.pos[t][1]);
  if (strategy == 0) return 0;
  if (strategy == 1) return own;
  if (strategy == 2) return enemy;
  if (strategy == 3) return std::min(own, enemy) * 7 + own + enemy;
  if (strategy == 4) return -enemy;
  if (strategy == 5 || strategy == 6) {
    int sum = 0;
    for (int p = 0; p < N; p++)
      if (geo.outer[p] < 0 && s.b[p].h && s.b[p].owner() == c)
        sum += geo.distance[t][p];
    return strategy == 5 ? -sum : sum;
  }
  if (strategy == 7) return -radius;
  if (strategy == 8) return radius;
  if (strategy == 9) {
    int score = 0;
    for (int n : geo.neighbors[t])
      if (s.b[n].h && s.b[n].owner() != c) {
        int exits = 0;
        for (int u : geo.neighbors[n])
          if (!s.b[u].h && u != t) exits++;
        score += 6 - exits;
      }
    return score;
  }
  if (strategy == 10) {
    State after = s;
    step(after, {'p', -1, t, 0});
    after.res[c] = 0;
    return double(legal(after, true).size());
  }
  int bait = 0;
  for (int n : geo.neighbors[t])
    if (s.b[n].h == 1 && s.b[n].owner() != c) {
      int support = 0;
      // The enemy singleton moves from n to t. From t inspect the first
      // remaining stack on each ray: it can recapture exactly when its
      // height equals its distance to t. n has become empty.
      for (const auto& ray : geo.rays[t]) {
        for (int i = 0; i < int(ray.size()); i++) {
          int p = ray[i];
          if (geo.outer[p] >= 0) break;
          if (p == n || !s.b[p].h) continue;
          if (s.b[p].owner() == c && s.b[p].h == i + 1) support++;
          break;
        }
      }
      bait += support;
    }
  return bait * 7 + own - enemy;
}
double capture_score(const State& s, const Move& a) {
  int c = s.side;
  State after = s;
  step(after, a);
  after.side = 1 - c;
  auto replies = legal(after, true);
  int worst = 0;
  for (const auto& r : replies)
    if (r.t == 'c' && r.q == a.q) worst = std::max(worst, int(after.b[r.p].h));
  return double(s.b[a.q].h) - double(worst ? after.b[a.q].h : 0);
}
Move choose(const State& s, const std::vector<Move>& moves, int strategy,
            int policy, bool escape_first, RNG& rng) {
  std::vector<int> places, caps;
  for (int i = 0; i < int(moves.size()); i++) {
    if (moves[i].t == 'p') places.push_back(i);
    if (moves[i].t == 'c') caps.push_back(i);
  }
  if (escape_first) {
    std::vector<int> exits;
    for (int i = 0; i < int(moves.size()); i++)
      if (moves[i].t == 'e') exits.push_back(i);
    if (!exits.empty()) return moves[exits[rng.bounded(exits.size())]];
  }
  bool use_places = false, use_caps = false;
  if (!places.empty()) {
    if (policy == 1)
      use_places = true;
    else if (policy == 2)
      use_caps = !caps.empty(), use_places = caps.empty();
    else if (policy == 3)
      use_caps = s.res[s.side] <= 3 && !caps.empty(), use_places = !use_caps;
    else if (policy == 4 || policy == 5) {
      double best = -1e9;
      for (int i : caps) best = std::max(best, capture_score(s, moves[i]));
      double threshold = policy == 4 ? 1.0 : (s.res[s.side] > 6 ? 0.0 : 2.0);
      use_caps = !caps.empty() && best >= threshold;
      use_places = !use_caps;
    }
  }
  std::vector<int> eligible;
  if (use_caps) {
    if (policy == 4 || policy == 5) {
      double best = -1e9;
      for (int i : caps) {
        double score = capture_score(s, moves[i]);
        if (score > best) {
          best = score;
          eligible.clear();
        }
        if (score == best) eligible.push_back(i);
      }
    } else
      eligible = caps;
  } else if (use_places)
    eligible = places;
  else {
    int i = int(rng.bounded(moves.size()));
    if (moves[i].t != 'p' || strategy == 0) return moves[i];
    eligible = places;
  }
  if (!eligible.empty() && moves[eligible[0]].t == 'p' && strategy != 0) {
    double best = -1e30;
    std::vector<int> ties;
    for (int i : eligible) {
      double score = placement_score(s, moves[i].q, strategy);
      if (score > best) {
        best = score;
        ties.clear();
      }
      if (score == best) ties.push_back(i);
    }
    eligible.swap(ties);
  }
  return moves[eligible[rng.bounded(eligible.size())]];
}
double logadd(double a, double b) {
  if (a == -std::numeric_limits<double>::infinity()) return b;
  if (b == -std::numeric_limits<double>::infinity()) return a;
  double hi = std::max(a, b);
  return hi + std::log1p(std::exp(std::min(a, b) - hi));
}
struct Config {
  bool variant = false, verify = false, escape_first[2] = {false, false};
  bool early_escape_first[2] = {false, false};
  uint64_t games = 1000, seed = 42, start = 0;
  int threads = 1, limit = 536;
  int strategy[2] = {0, 0}, policy[2] = {0, 0};
  std::array<int, 3> schedule[2] = {{{-1, -1, -1}}, {{-1, -1, -1}}};
  std::string output, records;
  bool replay = false;
  uint64_t replay_id = 0;

  bool prefer_escape(const State& s) const {
    return escape_first[s.side] ||
           (early_escape_first[s.side] && s.res[1 - s.side] > 0);
  }
};
#include "game_records.hpp"
struct Stats {
  uint64_t games = 0, turns = 0, passes = 0, center_resets = 0,
           early_capture = 0, early_escape = 0, conservation_checks = 0;
  std::array<uint64_t, 6> outcomes{};
  std::array<uint64_t, 5> actions{};
  std::array<std::array<uint64_t, 5>, 2> actions_by_player{};
  std::array<uint64_t, 2> early_capture_by_player{}, early_escape_by_player{};
  std::array<uint64_t, 2> phase_turns{}, phase_choices{};
  std::array<uint64_t, 3> placement_phase_turns{}, placement_phase_choices{};
  std::array<uint64_t, 37> source_heights{}, max_heights{};
  std::array<std::array<uint64_t, 6>, 3> first_empty{};
  std::vector<uint64_t> duration, depth_n;
  std::vector<double> depth_logsum, depth_logsum2;
  double logtree_sum = -std::numeric_limits<double>::infinity(),
         logtree_sum2 = -std::numeric_limits<double>::infinity();
  explicit Stats(int limit)
      : duration(limit + 1),
        depth_n(limit + 1),
        depth_logsum(limit + 1, -std::numeric_limits<double>::infinity()),
        depth_logsum2(limit + 1, -std::numeric_limits<double>::infinity()) {}
  void add(const Stats& o) {
    games += o.games;
    turns += o.turns;
    passes += o.passes;
    center_resets += o.center_resets;
    early_capture += o.early_capture;
    early_escape += o.early_escape;
    conservation_checks += o.conservation_checks;
    for (int i = 0; i < 6; i++) outcomes[i] += o.outcomes[i];
    for (int i = 0; i < 5; i++) actions[i] += o.actions[i];
    for (int i = 0; i < 2; i++) {
      for (int j = 0; j < 5; j++)
        actions_by_player[i][j] += o.actions_by_player[i][j];
      early_capture_by_player[i] += o.early_capture_by_player[i];
      early_escape_by_player[i] += o.early_escape_by_player[i];
      phase_turns[i] += o.phase_turns[i];
      phase_choices[i] += o.phase_choices[i];
    }
    for (int i = 0; i < 3; i++) {
      placement_phase_turns[i] += o.placement_phase_turns[i];
      placement_phase_choices[i] += o.placement_phase_choices[i];
      for (int j = 0; j < 6; j++) first_empty[i][j] += o.first_empty[i][j];
    }
    for (int i = 0; i <= 36; i++) {
      source_heights[i] += o.source_heights[i];
      max_heights[i] += o.max_heights[i];
    }
    for (size_t i = 0; i < duration.size(); i++) {
      duration[i] += o.duration[i];
      depth_n[i] += o.depth_n[i];
      depth_logsum[i] = logadd(depth_logsum[i], o.depth_logsum[i]);
      depth_logsum2[i] = logadd(depth_logsum2[i], o.depth_logsum2[i]);
    }
    logtree_sum = logadd(logtree_sum, o.logtree_sum);
    logtree_sum2 = logadd(logtree_sum2, o.logtree_sum2);
  }
};
void game(const Config& cfg, uint64_t id, Stats& stats,
          RecordStore* records = nullptr, GameRecord* replay = nullptr) {
  bool recording = records || replay;
  GameRecord archive;
  if (recording) {
    archive.id = id;
    archive.moves.reserve(std::min(cfg.limit, 512));
  }
  State s;
  RNG rng{mix(cfg.seed ^ mix(id))};
  std::unordered_map<std::string, uint8_t> seen;
  seen.reserve(cfg.limit * 2);
  int first = -1, out = 5, length = 0, maxheight = 0;
  double logweight = 0, logtree = 0;
  for (int turn = 0; turn < cfg.limit; turn++) {
    if (++seen[key(s)] >= 3) {
      out = 3;
      break;
    }
    auto moves = legal(s, cfg.variant);
    int ph = s.res[s.side] > 0 ? 0 : 1;
    stats.phase_turns[ph]++;
    stats.phase_choices[ph] += moves.size();
    if (ph == 0) {
      int stage = (18 - s.res[s.side]) / 6;
      stats.placement_phase_turns[stage]++;
      stats.placement_phase_choices[stage] += moves.size();
    }
    stats.depth_n[turn]++;
    stats.depth_logsum[turn] = logadd(stats.depth_logsum[turn], logweight);
    stats.depth_logsum2[turn] =
        logadd(stats.depth_logsum2[turn], 2 * logweight);
    logweight += std::log(double(std::max<size_t>(1, moves.size())));
    logtree = logadd(logtree, logweight);
    stats.turns++;
    length++;
    if (moves.empty()) {
      if (recording) archive.append(s, {'x', -1, -1, 0}, 0, -1);
      stats.passes++;
      if (++s.passes == 2) {
        out = 4;
        break;
      }
    } else {
      s.passes = 0;
      int strat = cfg.strategy[s.side], stage = (18 - s.res[s.side]) / 6;
      if (stage < 3 && cfg.schedule[s.side][stage] >= 0)
        strat = cfg.schedule[s.side][stage];
      Move a = choose(s, moves, strat, cfg.policy[s.side], cfg.prefer_escape(s), rng);
      if (recording) archive.append(s, a, int(moves.size()), strat);
      if (a.t == 'p') {
        stats.actions[0]++;
        if (turn > 0 && empty_inside(s)) stats.center_resets++;
      }
      int action_index = a.t == 'p'   ? 0
                         : a.t == 'm' ? 1
                         : a.t == 'c' ? 2
                         : a.t == 's' ? 3
                                      : 4;
      stats.actions_by_player[s.side][action_index]++;
      if (a.t == 'c' && ph == 0) stats.early_capture_by_player[s.side]++;
      if (a.t == 'e' && s.res[1 - s.side] > 0)
        stats.early_escape_by_player[s.side]++;
      if (a.t == 'm') stats.actions[1]++;
      if (a.t == 'c') {
        stats.actions[2]++;
        stats.early_capture += ph == 0;
      }
      if (a.t == 's') stats.actions[3]++;
      if (a.t == 'e') {
        stats.actions[4]++;
        stats.early_escape += s.res[1 - s.side] > 0;
      }
      if (a.p >= 0) {
        stats.source_heights[s.b[a.p].h]++;
        maxheight = std::max(maxheight, int(s.b[a.p].h));
      } else
        maxheight = std::max(maxheight, 1);
      step(s, a);
      maxheight = std::max(maxheight, int(s.b[a.q].h));
      if (first < 0 && s.res[s.side] == 0) first = s.side;
      if (cfg.verify) {
        conservation(s);
        stats.conservation_checks++;
      }
      int r = result(s, cfg.variant);
      if (recording) archive.observe(s, r >= 0);
      if (r >= 0) {
        out = r;
        break;
      }
    }
    s.side = 1 - s.side;
  }
  stats.depth_n[length]++;
  stats.depth_logsum[length] = logadd(stats.depth_logsum[length], logweight);
  stats.depth_logsum2[length] =
      logadd(stats.depth_logsum2[length], 2 * logweight);
  conservation(s);
  stats.conservation_checks++;
  stats.games++;
  stats.outcomes[out]++;
  stats.duration[length]++;
  stats.max_heights[maxheight]++;
  stats.first_empty[first < 0 ? 2 : first][out]++;
  stats.logtree_sum = logadd(stats.logtree_sum, logtree);
  stats.logtree_sum2 = logadd(stats.logtree_sum2, 2 * logtree);
  if (recording) {
    archive.outcome = out;
    archive.max_height = maxheight;
    archive.final = record_totals(s);
    if (records) records->consider(cfg, archive);
    if (replay) *replay = std::move(archive);
  }
}
template <class C>
void array_json(std::ostream& o, const C& a) {
  o << '[';
  bool first = true;
  for (auto x : a) {
    if (!first) o << ',';
    first = false;
    o << x;
  }
  o << ']';
}
void double_json(std::ostream& o, double x) {
  if (std::isfinite(x))
    o << x;
  else
    o << "null";
}
void output_json(std::ostream& o, const Config& c, const Stats& s,
                 double seconds) {
  o << std::setprecision(17) << "{\"schema\":2,\"variant\":\""
    << (c.variant ? 'B' : 'A') << "\",\"games\":" << s.games
    << ",\"seed\":" << c.seed << ",\"start\":" << c.start
    << ",\"limit\":" << c.limit << ",\"threads\":" << c.threads
    << ",\"white\":" << c.strategy[0] << ",\"black\":" << c.strategy[1]
    << ",\"white_policy\":" << c.policy[0]
    << ",\"black_policy\":" << c.policy[1]
    << ",\"white_escape_first\":" << (c.escape_first[0] ? "true" : "false")
    << ",\"black_escape_first\":" << (c.escape_first[1] ? "true" : "false")
    << ",\"white_early_escape_first\":" << (c.early_escape_first[0] ? "true" : "false")
    << ",\"black_early_escape_first\":" << (c.early_escape_first[1] ? "true" : "false")
    << ",\"white_schedule\":";
  array_json(o, c.schedule[0]);
  o << ",\"black_schedule\":";
  array_json(o, c.schedule[1]);
  o << ",\"verify_every_step\":" << (c.verify ? "true" : "false")
    << ",\"seconds\":" << seconds << ",\"turns\":" << s.turns
    << ",\"passes\":" << s.passes << ",\"center_resets\":" << s.center_resets
    << ",\"early_capture\":" << s.early_capture
    << ",\"early_escape\":" << s.early_escape
    << ",\"conservation_checks\":" << s.conservation_checks << ",\"outcomes\":";
  array_json(o, s.outcomes);
  o << ",\"actions\":";
  array_json(o, s.actions);
  o << ",\"actions_by_player\":[";
  array_json(o, s.actions_by_player[0]);
  o << ',';
  array_json(o, s.actions_by_player[1]);
  o << "],\"early_capture_by_player\":";
  array_json(o, s.early_capture_by_player);
  o << ",\"early_escape_by_player\":";
  array_json(o, s.early_escape_by_player);
  o << ",\"phase_turns\":";
  array_json(o, s.phase_turns);
  o << ",\"phase_choices\":";
  array_json(o, s.phase_choices);
  o << ",\"placement_phase_turns\":";
  array_json(o, s.placement_phase_turns);
  o << ",\"placement_phase_choices\":";
  array_json(o, s.placement_phase_choices);
  o << ",\"source_heights\":";
  array_json(o, s.source_heights);
  o << ",\"max_heights\":";
  array_json(o, s.max_heights);
  o << ",\"first_empty\":[";
  for (int i = 0; i < 3; i++) {
    if (i) o << ',';
    array_json(o, s.first_empty[i]);
  }
  o << "],\"duration\":";
  array_json(o, s.duration);
  bool valid = c.strategy[0] == 0 && c.strategy[1] == 0 && c.policy[0] == 0 &&
               c.policy[1] == 0 && !c.escape_first[0] && !c.escape_first[1] &&
               !c.early_escape_first[0] && !c.early_escape_first[1];
  for (auto schedule : c.schedule)
    for (int x : schedule) valid = valid && x < 0;
  o << ",\"tree_estimator_valid\":" << (valid ? "true" : "false")
    << ",\"tree_logsum\":";
  double_json(o, s.logtree_sum);
  o << ",\"tree_logsum2\":";
  double_json(o, s.logtree_sum2);
  o << ",\"depth_n\":";
  array_json(o, s.depth_n);
  o << ",\"depth_logsum\":[";
  for (size_t i = 0; i < s.depth_logsum.size(); i++) {
    if (i) o << ',';
    double_json(o, s.depth_logsum[i]);
  }
  o << "],\"depth_logsum2\":[";
  for (size_t i = 0; i < s.depth_logsum2.size(); i++) {
    if (i) o << ',';
    double_json(o, s.depth_logsum2[i]);
  }
  o << "]}\n";
}
void protocol() {
  std::string line;
  while (std::getline(std::cin, line)) {
    try {
      std::istringstream in(line);
      char v;
      State s;
      in >> v >> s.side >> s.res[0] >> s.res[1];
      for (int p = 0; p < N; p++) {
        std::string tok;
        if (!(in >> tok)) throw std::runtime_error("127 stack tokens required");
        if (tok != "-") {
          if (tok.size() > 36) throw std::runtime_error("stack >36");
          s.b[p].h = uint8_t(tok.size());
          for (size_t j = 0; j < tok.size(); j++) {
            if (tok[j] != '0' && tok[j] != '1')
              throw std::runtime_error("invalid colour");
            s.b[p].bits |= uint64_t(tok[j] - '0') << j;
          }
        }
      }
      auto moves = legal(s, v == 'B' || v == '1');
      std::ostringstream out;
      out << "{\"moves\":[";
      for (size_t i = 0; i < moves.size(); i++) {
        if (i) out << ',';
        auto a = moves[i];
        out << "[\"" << a.t << "\"," << a.p << ',' << a.q << ',' << a.k << ']';
      }
      out << "],\"result\":" << result(s, v == 'B' || v == '1');
      Move a;
      if (in >> a.t >> a.p >> a.q >> a.k) {
        bool ok = false;
        for (auto m : moves)
          if (m.t == a.t && m.p == a.p && m.q == a.q && m.k == a.k) ok = true;
        if (!ok) throw std::runtime_error("requested action not legal");
        step(s, a);
        int applied = result(s, v == 'B' || v == '1');
        s.side = 1 - s.side;
        out << ",\"state\":[";
        for (int p = 0; p < N; p++) {
          if (p) out << ',';
          out << '\"';
          if (!s.b[p].h)
            out << '-';
          else
            for (int j = 0; j < s.b[p].h; j++) out << ((s.b[p].bits >> j) & 1);
          out << '\"';
        }
        out << "],\"res\":[" << s.res[0] << ',' << s.res[1]
            << "],\"side\":" << s.side << ",\"applied_result\":" << applied;
      }
      out << '}';
      std::cout << out.str() << '\n' << std::flush;
    } catch (const std::exception& e) {
      std::cout << "{\"error\":\"" << e.what() << "\"}\n" << std::flush;
    }
  }
}
Config parse(int argc, char** argv) {
  Config c;
  for (int i = 1; i < argc; i++) {
    std::string k = argv[i];
    if (k == "--verify-every-step") {
      c.verify = true;
      continue;
    }
    if (k == "--white-escape-first" || k == "--black-escape-first") {
      c.escape_first[k == "--white-escape-first" ? 0 : 1] = true;
      continue;
    }
    if (k == "--white-early-escape-first" || k == "--black-early-escape-first") {
      c.early_escape_first[k == "--white-early-escape-first" ? 0 : 1] = true;
      continue;
    }
    if (i + 1 >= argc) throw std::runtime_error("missing value for " + k);
    std::string v = argv[++i];
    if (k == "--variant") {
      if (v != "A" && v != "B")
        throw std::runtime_error("variant A or B required");
      c.variant = v == "B";
    } else if (k == "--games")
      c.games = std::stoull(v);
    else if (k == "--seed")
      c.seed = std::stoull(v);
    else if (k == "--start")
      c.start = std::stoull(v);
    else if (k == "--threads")
      c.threads = std::stoi(v);
    else if (k == "--limit")
      c.limit = std::stoi(v);
    else if (k == "--white")
      c.strategy[0] = std::stoi(v);
    else if (k == "--black")
      c.strategy[1] = std::stoi(v);
    else if (k == "--policy")
      c.policy[0] = c.policy[1] = std::stoi(v);
    else if (k == "--white-policy")
      c.policy[0] = std::stoi(v);
    else if (k == "--black-policy")
      c.policy[1] = std::stoi(v);
    else if (k == "--output")
      c.output = v;
    else if (k == "--records")
      c.records = v;
    else if (k == "--replay") {
      c.replay = true;
      c.replay_id = std::stoull(v);
    }
    else if (k == "--white-schedule" || k == "--black-schedule") {
      int side = k == "--white-schedule" ? 0 : 1;
      std::replace(v.begin(), v.end(), ',', ' ');
      std::istringstream in(v);
      for (int& x : c.schedule[side])
        if (!(in >> x))
          throw std::runtime_error("three schedule values required");
    } else
      throw std::runtime_error("unknown option " + k);
  }
  if (c.threads < 1 || c.threads > 256 || c.limit < 1 || c.limit > 100000 ||
      c.games == 0)
    throw std::runtime_error("invalid run size/threads/limit");
  if (!c.records.empty() && (c.records == c.output || c.replay))
    throw std::runtime_error("records must use a separate output path and cannot combine with replay");
  for (int i = 0; i < 2; i++) {
    if (c.early_escape_first[i] && (!c.variant || c.escape_first[i]))
      throw std::runtime_error("early escape preference requires variant B and no general escape preference");
    if (c.strategy[i] < 0 || c.strategy[i] > 11 || c.policy[i] < 0 ||
        c.policy[i] > 5)
      throw std::runtime_error("invalid strategy/policy");
    for (int x : c.schedule[i])
      if (x < -1 || x > 11) throw std::runtime_error("invalid schedule");
  }
  return c;
}
}  // namespace staxxit
int main(int argc, char** argv) {
  using namespace staxxit;
  try {
    if (argc > 1 && (std::string(argv[1]) == "--protocol" ||
                     std::string(argv[1]) == "--probe")) {
      protocol();
      return 0;
    }
    Config c = parse(argc, argv);
    if (c.replay) {
      Stats single(c.limit);
      GameRecord trace;
      game(c, c.replay_id, single, nullptr, &trace);
      if (c.output.empty()) {
        record_trace(std::cout, c, trace);
        std::cout << '\n';
      } else {
        std::ofstream out(c.output);
        if (!out) throw std::runtime_error("cannot open replay output");
        record_trace(out, c, trace);
        out << '\n';
        if (!out) throw std::runtime_error("replay output write failure");
      }
      return 0;
    }
    auto start = std::chrono::steady_clock::now();
    Stats total(c.limit);
    RecordStore records;
    std::atomic<uint64_t> next{0};
    std::mutex mutex;
    std::vector<std::thread> workers;
    std::exception_ptr error;
    for (int t = 0; t < c.threads; t++)
      workers.emplace_back([&] {
        try {
          Stats local(c.limit);
          RecordStore local_records;
          for (;;) {
            uint64_t first = next.fetch_add(64);
            if (first >= c.games) break;
            uint64_t end = std::min(first + 64, c.games);
            for (uint64_t i = first; i < end; i++)
              game(c, c.start + i, local, c.records.empty() ? nullptr : &local_records);
          }
          std::lock_guard<std::mutex> lock(mutex);
          total.add(local);
          if (!c.records.empty()) records.add(local_records);
        } catch (...) {
          std::lock_guard<std::mutex> lock(mutex);
          error = std::current_exception();
          next = c.games;
        }
      });
    for (auto& t : workers) t.join();
    if (error) std::rethrow_exception(error);
    double seconds =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
            .count();
    if (c.output.empty())
      output_json(std::cout, c, total, seconds);
    else {
      std::ofstream out(c.output);
      if (!out) throw std::runtime_error("cannot open output");
      output_json(out, c, total, seconds);
      if (!out) throw std::runtime_error("output write failure");
    }
    std::cerr << "completed " << total.games << " games, "
              << total.games / seconds << " games/s, " << seconds << " s\n";
    if (!c.records.empty()) {
      std::ofstream out(c.records);
      if (!out) throw std::runtime_error("cannot open records output");
      record_catalog(out, c, records);
      if (!out) throw std::runtime_error("records output write failure");
    }
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "error: " << e.what() << '\n';
    return 1;
  }
}
