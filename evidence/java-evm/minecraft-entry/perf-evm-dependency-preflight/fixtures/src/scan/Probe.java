package scan;

public class Probe extends Base implements Marker {
    private static Helper current;

    static {
        current = new Helper();
    }

    public Probe() {
        super();
        current = new Helper();
    }

    public static Object dependencies(Object value) {
        Helper helper = new Helper();
        Object[] array = new Helper[2];
        Helper cast = (Helper) value;
        boolean marker = value instanceof Marker;
        return marker ? array : cast;
    }

    public static Helper getCurrent() { return current; }
    public static void setCurrent(Helper value) { current = value; }
    public static String interfaceCall(Marker value) { return value.markerName(); }
    public static String virtualCall(Object value) { return value.toString(); }
    public static Helper staticCall() { return Helper.make(); }
    public static Class<?> classLiteral() { return Helper.class; }

    public static int tableSwitch(int value) {
        switch (value) {
            case 0: return 11;
            case 1: return 22;
            case 2: return 33;
            case 3: return 44;
            case 4: return 55;
            case 5: return 66;
            default: return -1;
        }
    }

    public static int lookupSwitch(int value) {
        switch (value) {
            case -4000: return 1;
            case 17: return 2;
            case 999: return 3;
            case 20000: return 4;
            default: return 0;
        }
    }

    public static int operandTrap() { return (short) 0xB7B6; }

    public static String fixturePadding() { return "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"; }

    public static int wideLocals() {
        int v000 = 0;
        int v001 = 1;
        int v002 = 2;
        int v003 = 3;
        int v004 = 4;
        int v005 = 5;
        int v006 = 6;
        int v007 = 7;
        int v008 = 8;
        int v009 = 9;
        int v010 = 10;
        int v011 = 11;
        int v012 = 12;
        int v013 = 13;
        int v014 = 14;
        int v015 = 15;
        int v016 = 16;
        int v017 = 17;
        int v018 = 18;
        int v019 = 19;
        int v020 = 20;
        int v021 = 21;
        int v022 = 22;
        int v023 = 23;
        int v024 = 24;
        int v025 = 25;
        int v026 = 26;
        int v027 = 27;
        int v028 = 28;
        int v029 = 29;
        int v030 = 30;
        int v031 = 31;
        int v032 = 32;
        int v033 = 33;
        int v034 = 34;
        int v035 = 35;
        int v036 = 36;
        int v037 = 37;
        int v038 = 38;
        int v039 = 39;
        int v040 = 40;
        int v041 = 41;
        int v042 = 42;
        int v043 = 43;
        int v044 = 44;
        int v045 = 45;
        int v046 = 46;
        int v047 = 47;
        int v048 = 48;
        int v049 = 49;
        int v050 = 50;
        int v051 = 51;
        int v052 = 52;
        int v053 = 53;
        int v054 = 54;
        int v055 = 55;
        int v056 = 56;
        int v057 = 57;
        int v058 = 58;
        int v059 = 59;
        int v060 = 60;
        int v061 = 61;
        int v062 = 62;
        int v063 = 63;
        int v064 = 64;
        int v065 = 65;
        int v066 = 66;
        int v067 = 67;
        int v068 = 68;
        int v069 = 69;
        int v070 = 70;
        int v071 = 71;
        int v072 = 72;
        int v073 = 73;
        int v074 = 74;
        int v075 = 75;
        int v076 = 76;
        int v077 = 77;
        int v078 = 78;
        int v079 = 79;
        int v080 = 80;
        int v081 = 81;
        int v082 = 82;
        int v083 = 83;
        int v084 = 84;
        int v085 = 85;
        int v086 = 86;
        int v087 = 87;
        int v088 = 88;
        int v089 = 89;
        int v090 = 90;
        int v091 = 91;
        int v092 = 92;
        int v093 = 93;
        int v094 = 94;
        int v095 = 95;
        int v096 = 96;
        int v097 = 97;
        int v098 = 98;
        int v099 = 99;
        int v100 = 100;
        int v101 = 101;
        int v102 = 102;
        int v103 = 103;
        int v104 = 104;
        int v105 = 105;
        int v106 = 106;
        int v107 = 107;
        int v108 = 108;
        int v109 = 109;
        int v110 = 110;
        int v111 = 111;
        int v112 = 112;
        int v113 = 113;
        int v114 = 114;
        int v115 = 115;
        int v116 = 116;
        int v117 = 117;
        int v118 = 118;
        int v119 = 119;
        int v120 = 120;
        int v121 = 121;
        int v122 = 122;
        int v123 = 123;
        int v124 = 124;
        int v125 = 125;
        int v126 = 126;
        int v127 = 127;
        int v128 = 128;
        int v129 = 129;
        int v130 = 130;
        int v131 = 131;
        int v132 = 132;
        int v133 = 133;
        int v134 = 134;
        int v135 = 135;
        int v136 = 136;
        int v137 = 137;
        int v138 = 138;
        int v139 = 139;
        int v140 = 140;
        int v141 = 141;
        int v142 = 142;
        int v143 = 143;
        int v144 = 144;
        int v145 = 145;
        int v146 = 146;
        int v147 = 147;
        int v148 = 148;
        int v149 = 149;
        int v150 = 150;
        int v151 = 151;
        int v152 = 152;
        int v153 = 153;
        int v154 = 154;
        int v155 = 155;
        int v156 = 156;
        int v157 = 157;
        int v158 = 158;
        int v159 = 159;
        int v160 = 160;
        int v161 = 161;
        int v162 = 162;
        int v163 = 163;
        int v164 = 164;
        int v165 = 165;
        int v166 = 166;
        int v167 = 167;
        int v168 = 168;
        int v169 = 169;
        int v170 = 170;
        int v171 = 171;
        int v172 = 172;
        int v173 = 173;
        int v174 = 174;
        int v175 = 175;
        int v176 = 176;
        int v177 = 177;
        int v178 = 178;
        int v179 = 179;
        int v180 = 180;
        int v181 = 181;
        int v182 = 182;
        int v183 = 183;
        int v184 = 184;
        int v185 = 185;
        int v186 = 186;
        int v187 = 187;
        int v188 = 188;
        int v189 = 189;
        int v190 = 190;
        int v191 = 191;
        int v192 = 192;
        int v193 = 193;
        int v194 = 194;
        int v195 = 195;
        int v196 = 196;
        int v197 = 197;
        int v198 = 198;
        int v199 = 199;
        int v200 = 200;
        int v201 = 201;
        int v202 = 202;
        int v203 = 203;
        int v204 = 204;
        int v205 = 205;
        int v206 = 206;
        int v207 = 207;
        int v208 = 208;
        int v209 = 209;
        int v210 = 210;
        int v211 = 211;
        int v212 = 212;
        int v213 = 213;
        int v214 = 214;
        int v215 = 215;
        int v216 = 216;
        int v217 = 217;
        int v218 = 218;
        int v219 = 219;
        int v220 = 220;
        int v221 = 221;
        int v222 = 222;
        int v223 = 223;
        int v224 = 224;
        int v225 = 225;
        int v226 = 226;
        int v227 = 227;
        int v228 = 228;
        int v229 = 229;
        int v230 = 230;
        int v231 = 231;
        int v232 = 232;
        int v233 = 233;
        int v234 = 234;
        int v235 = 235;
        int v236 = 236;
        int v237 = 237;
        int v238 = 238;
        int v239 = 239;
        int v240 = 240;
        int v241 = 241;
        int v242 = 242;
        int v243 = 243;
        int v244 = 244;
        int v245 = 245;
        int v246 = 246;
        int v247 = 247;
        int v248 = 248;
        int v249 = 249;
        int v250 = 250;
        int v251 = 251;
        int v252 = 252;
        int v253 = 253;
        int v254 = 254;
        int v255 = 255;
        int v256 = 256;
        int v257 = 257;
        int v258 = 258;
        int v259 = 259;
        int v260 = 260;
        v260++;
        return v000 + v001 + v002 + v003 + v004 + v005 + v006 + v007 + v008 + v009
            + v010 + v011 + v012 + v013 + v014 + v015 + v016 + v017 + v018 + v019
            + v020 + v021 + v022 + v023 + v024 + v025 + v026 + v027 + v028 + v029
            + v030 + v031 + v032 + v033 + v034 + v035 + v036 + v037 + v038 + v039
            + v040 + v041 + v042 + v043 + v044 + v045 + v046 + v047 + v048 + v049
            + v050 + v051 + v052 + v053 + v054 + v055 + v056 + v057 + v058 + v059
            + v060 + v061 + v062 + v063 + v064 + v065 + v066 + v067 + v068 + v069
            + v070 + v071 + v072 + v073 + v074 + v075 + v076 + v077 + v078 + v079
            + v080 + v081 + v082 + v083 + v084 + v085 + v086 + v087 + v088 + v089
            + v090 + v091 + v092 + v093 + v094 + v095 + v096 + v097 + v098 + v099
            + v100 + v101 + v102 + v103 + v104 + v105 + v106 + v107 + v108 + v109
            + v110 + v111 + v112 + v113 + v114 + v115 + v116 + v117 + v118 + v119
            + v120 + v121 + v122 + v123 + v124 + v125 + v126 + v127 + v128 + v129
            + v130 + v131 + v132 + v133 + v134 + v135 + v136 + v137 + v138 + v139
            + v140 + v141 + v142 + v143 + v144 + v145 + v146 + v147 + v148 + v149
            + v150 + v151 + v152 + v153 + v154 + v155 + v156 + v157 + v158 + v159
            + v160 + v161 + v162 + v163 + v164 + v165 + v166 + v167 + v168 + v169
            + v170 + v171 + v172 + v173 + v174 + v175 + v176 + v177 + v178 + v179
            + v180 + v181 + v182 + v183 + v184 + v185 + v186 + v187 + v188 + v189
            + v190 + v191 + v192 + v193 + v194 + v195 + v196 + v197 + v198 + v199
            + v200 + v201 + v202 + v203 + v204 + v205 + v206 + v207 + v208 + v209
            + v210 + v211 + v212 + v213 + v214 + v215 + v216 + v217 + v218 + v219
            + v220 + v221 + v222 + v223 + v224 + v225 + v226 + v227 + v228 + v229
            + v230 + v231 + v232 + v233 + v234 + v235 + v236 + v237 + v238 + v239
            + v240 + v241 + v242 + v243 + v244 + v245 + v246 + v247 + v248 + v249
            + v250 + v251 + v252 + v253 + v254 + v255 + v256 + v257 + v258 + v259 + v260;
    }
}
