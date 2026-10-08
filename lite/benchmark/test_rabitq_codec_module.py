# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Check the extracted codec against the recorded pre-extraction implementation."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

BASE = "03c235711af42797787003f7816e6fba8bc26973"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    original = subprocess.check_output(["git", "show", BASE+":lite/benchmark/rabitq_lite_codec_probe.cpp"], cwd=root, text=True)
    core = original[original.index("void\nfht("):original.index("float\nfilter_centered_ip(")]
    core = core.replace("require(", "codec_require(")
    core = re.sub(r"^(void|uint64_t|Model|std::vector<uint8_t>|std::vector<float>|Encoded|uint32_t|float)\n", r"inline \1\n", core, flags=re.M)
    constants = original[original.index("constexpr uint32_t K_TOTAL_BITS"):original.index("using Clock")]
    historical = '#include "lite/rabitq_codec.h"\nnamespace historical {\n'+constants+'inline void codec_require(bool v,const char* m) { if(!v) throw std::runtime_error(m); }\n'+core+'}\n'
    driver = r"""
#include "historical.h"
#include <cstring>
#include <iostream>
#include <limits>
namespace current = vsag::lite::detail::rabitq;
uint64_t second_translation_unit();
int main() {
    if (second_translation_unit() != 8) return 1;
    uint64_t checked = 0;
    for (uint64_t dim : {1, 7, 8, 17, 128, 768, 960}) {
        std::vector<float> base(4 * dim);
        for (uint64_t i = 0; i < base.size(); ++i) base[i] = float(int(i % 31) - 15) / 16;
        auto old = historical::train(base, 4, dim, 47);
        auto now = current::train(base, 4, dim, 47);
        if (old.centroid != now.centroid || old.flips != now.flips) return 2;
        for (uint64_t row = 0; row < 4; ++row) {
            std::vector<float> values(base.begin() + row * dim, base.begin() + (row + 1) * dim);
            const auto reference = values;
            now.Transform(values);
            now.InverseTransform(values);
            for (uint64_t d = 0; d < dim; ++d) {
                if (std::fabs(values[d] - reference[d]) > 2e-5F) return 7;
            }
        }
        current::EncodedRecords records(dim);
        for (uint64_t row = 0; row < 4; ++row) {
            auto a = historical::encode(old, base.data() + row * dim);
            auto b = current::encode(now, base.data() + row * dim);
            if (a.filter != b.filter || a.supplement != b.supplement || a.scalar != b.scalar) return 3;
            const float x[] = {a.norm,a.code_norm,a.error,a.filter_norm,a.filter_error,a.lower_bound_error};
            const float y[] = {b.norm,b.code_norm,b.error,b.filter_norm,b.filter_error,b.lower_bound_error};
            if (std::memcmp(x,y,sizeof(x))) return 4;
            records.Append(b);
            std::vector<float> scratch;
            const float* pointer = current::decode(now, records.At(row), scratch);
            if (pointer != scratch.data() || scratch.size() != dim) return 8;
            // Independently construct transformed quantized reconstruction from
            // scalar bytes, then verify the decoded value by forward transform.
            std::vector<float> projected = scratch;
            now.Transform(projected);
            for (uint64_t d = 0; d < dim; ++d) {
                const float expected = (float(a.scalar[d]) - 127.5F) * a.norm / a.code_norm + old.centroid[d];
                if (std::fabs(projected[d] - expected) > 3e-5F * std::max(1.0F,std::fabs(expected))) return 9;
            }
            std::vector<float> other;
            const auto preserved = scratch;
            (void)current::decode(now, records.At(row), other);
            if (scratch != preserved || other.data() == pointer) return 10;
            ++checked;
        }
        records.Replace(1,current::encode(now,base.data()));
        records.RemoveSwap(0);
        if (records.Size() != 3) return 5;
        bool rejected = false;
        try { (void)records.At(3); } catch (const std::runtime_error&) { rejected = true; }
        if (!rejected) return 6;
        auto invalid = now;
        invalid.flips.clear();
        std::vector<float> scratch;
        rejected = false;
        try { (void)current::decode(invalid, records.At(0), scratch); }
        catch (const std::runtime_error&) { rejected = true; }
        if (!rejected) return 11;
        auto view = records.At(0);
        view.metadata.code_norm = 0;
        rejected = false;
        try { (void)current::decode(now, view, scratch); }
        catch (const std::runtime_error&) { rejected = true; }
        if (!rejected) return 12;
        view = records.At(0);
        view.metadata.norm = std::numeric_limits<float>::infinity();
        rejected = false;
        try { (void)current::decode(now, view, scratch); }
        catch (const std::runtime_error&) { rejected = true; }
        if (!rejected) return 13;
    }
    std::cout << "PASS: " << checked << " exact records, 7 dimensions, 2 translation units, inverse/decode ownership checks\n";
}
"""
    second = '#include "lite/rabitq_codec.h"\nuint64_t second_translation_unit() { return vsag::lite::detail::rabitq::K_TOTAL_BITS; }\n'
    with tempfile.TemporaryDirectory(prefix="vsag-codec-module-") as directory:
        temp = Path(directory)
        (temp/"historical.h").write_text(historical)
        (temp/"main.cpp").write_text(driver)
        (temp/"second.cpp").write_text(second)
        binary = temp/"test"
        command = [os.environ.get("CXX","c++"),"-std=c++17","-Wall","-Wextra","-I"+str(root/"src"),str(temp/"main.cpp"),str(temp/"second.cpp"),"-o",str(binary)]
        command += ["-O1","-g","-fsanitize=address,undefined","-fno-omit-frame-pointer"] if args.sanitize else ["-O2"]
        subprocess.run(command,check=True)
        subprocess.run([str(binary)],check=True)


if __name__ == "__main__":
    main()
