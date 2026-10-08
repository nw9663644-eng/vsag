# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Compile an external public-API consumer and inject transactional allocation failures."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build",type=Path)
    parser.add_argument("--disabled",action="store_true")
    parser.add_argument("--sanitize",action="store_true")
    parser.add_argument("--static",action="store_true")
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    build=args.build.resolve()
    source=r"""
#include "vsag/lite/index.h"
#include <cstdlib>
#include <iostream>
#include <new>
#include <sstream>
static int fail_after=-1;
void* operator new(std::size_t size) {
    if (fail_after == 0) { fail_after=-1; throw std::bad_alloc(); }
    if (fail_after > 0) --fail_after;
    if (auto* result=std::malloc(size ? size : 1)) return result;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p,std::size_t) noexcept { std::free(p); }
void* operator new[](std::size_t n) { return ::operator new(n); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete[](void* p,std::size_t) noexcept { std::free(p); }
std::string save(const vsag::lite::Index& index) {
    std::ostringstream output;
    if(!index.Save(output)) throw std::runtime_error("save");
    return output.str();
}
int main(int argc,char**) {
    auto created=vsag::lite::Index::Create(3);
    if(!created) return 1;
    auto& index=**created;
    float a[]={0,1,2}, b[]={2,1,0};
    if(!index.Add(42,a,3)||!index.Add(7,b,3)) return 2;
    auto built=index.BuildGraph(vsag::lite::VectorStorage::RABITQ8,2,8);
    if(argc>1) {
        if(built || built.error().type!=vsag::ErrorType::UNSUPPORTED_INDEX_OPERATION || index.Size()!=2 || index.ActiveBackend()!=vsag::lite::BackendKind::BRUTE_FORCE) return 3;
        std::cout<<"PASS: disabled build rejects RaBitQ and retains flat contents\n";
        return 0;
    }
    if(!built) return 4;
    const auto baseline=save(index);
    int total_failures=0;
    for(int operation=0;operation<3;++operation) {
        int failures=0;
        bool success=false;
        for(int point=0;point<256;++point) {
            std::istringstream input(baseline);
            auto loaded=vsag::lite::Index::Load(input);
            if(!loaded) return 5;
            fail_after=point;
            bool ok;
            if(operation==2) ok=(*loaded)->Remove(42);
            else {
                auto result=operation==0 ? (*loaded)->Add(9,a,3) : (*loaded)->Update(42,b,3);
                ok=bool(result);
                if(!ok && result.error().type!=vsag::ErrorType::NO_ENOUGH_MEMORY) return 6;
            }
            fail_after=-1;
            if(ok) { success=true; break; }
            ++failures;
            if(save(**loaded)!=baseline) return 7;
        }
        if(!success || failures==0) return 8;
        total_failures+=failures;
    }
    std::cout<<"PASS: "<<total_failures<<" injected Add/Update/Remove allocation failures retained exact snapshots\n";
}
"""
    with tempfile.TemporaryDirectory(prefix="vsag-rabitq-consumer-") as temp:
        directory=Path(temp)
        (directory/"main.cpp").write_text(source)
        binary=directory/"test"
        command=[os.environ.get("CXX","c++"),"-std=c++17","-I"+str(root/"include"),str(directory/"main.cpp"),"-L"+str(build),"-Wl,-rpath,"+str(build),"-lvsag-lite","-o",str(binary)]
        if args.static:
            command[command.index("-lvsag-lite")] = str(build/"libvsag-lite.a")
        if args.sanitize:command += ["-fsanitize=address,undefined","-fno-omit-frame-pointer"]
        subprocess.run(command,check=True)
        subprocess.run([str(binary)]+(["disabled"] if args.disabled else []),check=True)


if __name__=="__main__":
    main()
