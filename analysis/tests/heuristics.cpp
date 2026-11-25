// Isolated tests of the production heuristic functions.
#define main staxxit_cli_main
#include "../staxxit.cpp"
#undef main

using namespace staxxit;

void require(bool condition, const char* message) {
  if (!condition) throw std::runtime_error(message);
}
int at(int q, int r) { return geo.index[q + 6][r + 6]; }
bool equal(Move a, Move b) {
  return a.t == b.t && a.p == b.p && a.q == b.q && a.k == b.k;
}
bool contains(const std::vector<Move>& moves, Move a) {
  return std::any_of(moves.begin(), moves.end(), [a](Move b) { return equal(a, b); });
}

int main() {
  try {
    // Two adjacent own singletons each have five empty neighboring inner
    // destinations. An adjacent opponent instead forces exactly one capture.
    State mobility;
    mobility.b[at(0, 0)] = {0, 1};
    require(placement_score(mobility, at(0, 1), 10) == 10, "mobility: ten free moves");
    mobility.b[at(0, 2)] = {1, 1};
    require(placement_score(mobility, at(0, 1), 10) == 1, "mobility: mandatory capture");
    require(placement_score(mobility, at(1, 0), 10) == 10, "mobility: alternative avoids capture");
    RNG mobility_rng{123};
    Move mobile = choose(mobility, legal(mobility, true), 10, 1, false, mobility_rng);
    require(mobile.t == 'p' && placement_score(mobility, mobile.q, 10) == 10,
            "mobility chooser must maximize its score");

    // The enemy singleton can capture a placement on (0,1); our singleton
    // at the center can immediately recapture it. Adding a second adjacent
    // friendly singleton creates two exact recapture possibilities.
    State bait;
    bait.b[at(0, 0)] = {0, 1};
    bait.b[at(1, 0)] = {1, 1};
    require(placement_score(bait, at(0, 1), 11) == 7, "bait: one recapture");
    bait.b[at(-1, 1)] = {0, 1};
    require(placement_score(bait, at(0, 1), 11) == 15, "bait: two recaptures");

    State policy;
    policy.b[at(0, 0)] = {0, 1};
    policy.b[at(1, 0)] = {1, 1};
    auto options = legal(policy, true);
    RNG rng{42};
    require(choose(policy, options, 0, 1, false, rng).t == 'p', "place-first policy");
    require(choose(policy, options, 0, 2, false, rng).t == 'c', "capture-first policy");
    policy.res[0] = 4;
    require(choose(policy, options, 0, 3, false, rng).t == 'p', "retain policy before threshold");
    policy.res[0] = 3;
    require(choose(policy, options, 0, 3, false, rng).t == 'c', "retain policy at threshold");
    require(choose(policy, options, 0, 4, false, rng).t == 'c', "tactical safe capture");
    policy.b[at(2, 0)] = {1, 1};
    options = legal(policy, true);
    require(choose(policy, options, 0, 4, false, rng).t == 'p', "tactical rejects recapture");
    for (int p = 0; p <= 5; p++)
      for (int strategy = 0; strategy < 12; strategy++)
        for (int k = 0; k < 20; k++)
          require(contains(options, choose(policy, options, strategy, p, false, rng)), "policy returned illegal move");

    State escape;
    escape.res[0] = 0;
    escape.res[1] = 1;
    escape.b[at(5, 0)] = {0, 1};
    escape.b[at(-5, 0)] = {1, 1};
    auto exits = legal(escape, true);
    require(choose(escape, exits, 0, 0, true, rng).t == 'e', "escape preference");
    Config early;
    early.variant = true;
    early.early_escape_first[0] = true;
    require(early.prefer_escape(escape), "early preference with opponent reserve");
    escape.res[1] = 0;
    require(!early.prefer_escape(escape), "early preference ends with opponent reserve");
    escape.res[1] = 1;
    escape.side = 1;
    require(!early.prefer_escape(escape), "early preference applies only to configured side");
    escape.side = 0;
    escape.b[at(4, 0)] = {1, 1};
    exits = legal(escape, true);
    require(choose(escape, exits, 0, 0, early.prefer_escape(escape), rng).t == 'c',
            "capture obligation above early escape preference");

    // Deterministic tie sampling over the six equal own-neighbor placements.
    // The fixed broad bounds detect a constant/strongly biased tie selector;
    // no platform-specific standard-library distribution is involved.
    State ties;
    ties.b[at(0, 0)] = {0, 1};
    auto six = legal(ties, false);
    require(six.size() == 6, "tie fixture: six placements");
    RNG left{20261125}, right{20261125};
    std::array<int, 127> counts{};
    for (int i = 0; i < 12000; i++) {
      Move a = choose(ties, six, 1, 1, false, left);
      Move b = choose(ties, six, 1, 1, false, right);
      require(equal(a, b), "seeded tie reproducibility");
      counts[a.q]++;
    }
    for (Move a : six) require(counts[a.q] > 1700 && counts[a.q] < 2300, "tie selection distribution");
    RNG known{0};
    require(known.next() == 0xe220a8397b1dcdafULL, "SplitMix64 known first output");
    for (int i = 0; i < 100; i++)
      require(known.bounded(0x8000000000000001ULL) < 0x8000000000000001ULL,
              "rejection-sampling range");
    std::cout << "{\"status\":\"passed\",\"groups\":6,\"policy_legality_checks\":1440,\"tie_draws\":12000}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
