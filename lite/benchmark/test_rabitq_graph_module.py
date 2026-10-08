# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Compare extracted mutable state with its frozen pre-extraction definition."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

BASE = "ec990a2bba5bfc7fb3ade33e9538749de7f7cfeb"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sanitize",action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    original = subprocess.check_output(["git","show",BASE+":lite/benchmark/rabitq_lite_codec_probe.cpp"],cwd=root,text=True)
    core = original[original.index("float\nfilter_centered_ip("):original.index("uint64_t\nresult_checksum(")]
    core = core.replace("filter_estimate(", "historical_filter_estimate(").replace("full_distance(", "historical_full_distance(")
    a = core.index("GraphTopology\nbuild_graph_topology(")
    b = core.index("struct GraphSearchResult")
    core = core[:a]+core[b:]
    core = core.replace("vsag::lite::experiment::select_rabitq_filter_ip()","vsag::lite::detail::rabitq::select_rabitq_filter_ip()")
    prefix = '#include "lite/rabitq_graph_state.h"\nnamespace historical {\nusing namespace vsag::lite::detail::rabitq;\ninline void require(bool v,const char* m) { codec_require(v,m); }\ninline double process_cpu_microseconds() { return 0.0; }\n'
    driver = r"""
#include "historical.h"
#include <cstring>
#include <iostream>
namespace current = vsag::lite::detail::rabitq;
int main() {
    constexpr uint64_t dim=17, count=8;
    std::vector<float> base(count*dim);
    for(uint64_t i=0;i<base.size();++i) base[i]=float(int(i%23)-11)/16;
    const auto model=current::train(base,count,dim,47);
    current::EncodedRecords codes(dim);
    for(uint64_t i=0;i<count;++i) codes.Append(current::encode(model,base.data()+i*dim));
    current::GraphTopology topology;
    historical::GraphTopology old_topology;
    topology.offsets.push_back(0);
    for(uint64_t i=0;i<count;++i) {
        topology.neighbors.push_back((i+1)%count);
        topology.neighbors.push_back((i+count-1)%count);
        topology.offsets.push_back(topology.neighbors.size());
    }
    old_topology.offsets=topology.offsets;
    old_topology.neighbors=topology.neighbors;
    std::vector<int64_t> ids={-8,70,42,9,100,11,22,33};
    uint64_t operations=0;
    for(bool incoming : {false,true}) {
        current::MutableGraphState now(model,codes,topology,ids,4,8,false,incoming);
        historical::MutableGraphState old(model,codes,old_topology,ids,4,8,false,incoming);
        const auto reject_all = now.SearchWithOptions(base.data(),4,0,[](int64_t){return false;});
        if(!reject_all.neighbors.empty() || reject_all.visited == 0 || reject_all.reordered != 0) return 16;
        const auto original_degree = now.GetMaxDegree();
        const auto original_budget = now.GetEfSearch();
        uint64_t callback_calls=0;
        const auto filtered=now.SearchWithOptions(base.data(),count,1000,[&](int64_t id){
            ++callback_calls;
            return id==42 || id==-8;
        });
        if(filtered.neighbors.size()!=2 || callback_calls!=count || filtered.visited!=count) return 17;
        for(const auto& neighbor:filtered.neighbors)
            if(now.IdAt(neighbor.id)!=42 && now.IdAt(neighbor.id)!=-8) return 18;
        if(now.GetEfSearch()!=original_budget || now.GetMaxDegree()!=original_degree) return 19;
        const auto zero=now.SearchWithOptions(base.data(),0,1,[&](int64_t){++callback_calls;return true;});
        if(!zero.neighbors.empty() || callback_calls!=count) return 20;
        if(now.SearchWithOptions(base.data(),3,1).neighbors.size()!=3) return 21;
        bool callback_threw=false;
        try { (void)now.SearchWithOptions(base.data(),3,8,[](int64_t)->bool{throw std::runtime_error("filter");}); }
        catch(const std::runtime_error&) {callback_threw=true;}
        if(!callback_threw) return 22;
        now.Validate();
        for(uint64_t cycle=0;cycle<60;++cycle) {
            const auto id=now.IdAt(cycle%now.Size());
            std::vector<float> vector(base.begin()+(cycle%count)*dim,base.begin()+(cycle%count+1)*dim);
            vector[cycle%dim]+=float(cycle+1)/32;
            if(now.Update(id,vector.data())!=old.Update(id,vector.data())) return 1;
            if(now.Remove(id)!=old.Remove(id)) return 2;
            if(now.Add(-1000-int64_t(cycle),vector.data())!=old.Add(-1000-int64_t(cycle),vector.data())) return 3;
            if(now.Add(-1000-int64_t(cycle),vector.data()) || old.Add(-1000-int64_t(cycle),vector.data())) return 4;
            now.Validate(); old.Validate();
            if(now.GetIds()!=old.GetIds()) return 5;
            auto a=now.GetGraph(); auto b=old.GetGraph();
            if(a.offsets!=b.offsets || a.neighbors!=b.neighbors) return 6;
            if(now.GetCodes().filters!=old.GetCodes().filters || now.GetCodes().supplements!=old.GetCodes().supplements) return 7;
            const auto& x=now.GetCodes().metadata;
            const auto& y=old.GetCodes().metadata;
            if(x.size()!=y.size() || std::memcmp(x.data(),y.data(),x.size()*sizeof(current::EncodedMetadata))) return 8;
            auto q=now.Search(base.data(),4); auto r=old.Search(base.data(),4);
            if(q.visited!=r.visited || q.reordered!=r.reordered || q.neighbors.size()!=r.neighbors.size()) return 9;
            for(uint64_t i=0;i<q.neighbors.size();++i)
                if(q.neighbors[i].id!=r.neighbors[i].id || q.neighbors[i].distance!=r.neighbors[i].distance) return 10;
            operations+=3;
        }
        while(now.Size()) {
            auto id=now.IdAt(now.Size()-1);
            if(!now.Remove(id)||!old.Remove(id)) return 11;
            now.Validate(); old.Validate();
        }
        if(!now.Search(base.data(),4).neighbors.empty() || now.Remove(999)) return 12;
        if(!now.Add(999,base.data()) || !old.Add(999,base.data())) return 13;
        now.Validate(); old.Validate();
        if(now.Search(base.data(),1).neighbors[0].id!=0) return 14;
    }
    // Identical vectors isolate external-ID tie ordering from slot ordering.
    std::vector<float> same(count*dim,1.0F);
    auto tie_model=current::train(same,count,dim,47);
    current::EncodedRecords tie_codes(dim);
    for(uint64_t i=0;i<count;++i) tie_codes.Append(current::encode(tie_model,same.data()));
    current::MutableGraphState ties(tie_model,tie_codes,topology,ids,4,8);
    for(const auto& result : {ties.SearchWithOptions(same.data(),3,8),
                              ties.SearchWithOptions(same.data(),3,8,[](int64_t){return true;})}) {
        if(result.neighbors.size()!=3) return 23;
        const std::vector<int64_t> expected={-8,9,11};
        for(uint64_t i=0;i<3;++i) if(ties.IdAt(result.neighbors[i].id)!=expected[i]) return 24;
    }
    for(const auto& bad : std::vector<current::GraphTopology>{
            {{}, {}}, {{1}, {}}, {{0, 2}, {0}}, {{0, 1, 0}, {0}}}) {
        bool rejected=false;
        try { (void)current::expand_graph(bad); }
        catch(const std::runtime_error&) { rejected=true; }
        if(!rejected) return 15;
    }
    std::cout<<"PASS: "<<operations<<" paired mutations; IDs/codes/topology/search exact, incoming on/off, filters/budgets/external-ID ties, empty/singleton\n";
}
"""
    with tempfile.TemporaryDirectory(prefix="vsag-graph-module-") as directory:
        temp=Path(directory)
        (temp/"historical.h").write_text(prefix+core+'}\n')
        (temp/"main.cpp").write_text(driver)
        command=[os.environ.get("CXX","c++"),"-std=c++17","-Wall","-Wextra","-I"+str(root/"src"),str(temp/"main.cpp"),str(root/"src/lite/rabitq_filter_ip.cpp"),"-o",str(temp/"test")]
        command += ["-O1","-g","-fsanitize=address,undefined","-fno-omit-frame-pointer"] if args.sanitize else ["-O2"]
        subprocess.run(command,check=True)
        subprocess.run([str(temp/"test")],check=True)


if __name__=="__main__":
    main()
