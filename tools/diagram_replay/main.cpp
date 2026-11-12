/**
 * @file main.cpp
 * @brief atugcc_diagram_replay CLI entry point (Spec 070-07)
 */
#include <iostream>
#include <string_view>
#include <vector>

#include "replay.hpp"

int main(int argc, char** argv) {
    std::vector<std::string_view> args;
    if (argc > 1 && argv != nullptr) {
        args.assign(argv + 1, argv + argc);
    }

    const auto parsed = atugcc::tools::replay::parseArgs(args, std::cerr);
    if (!parsed) {
        return 2;
    }

    std::ios::sync_with_stdio(false);
    return atugcc::tools::replay::replay(std::cin, std::cout, std::cerr, *parsed);
}
